from ctypes import ARRAY, c_int
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem.rstr import string_repr, emptystr
from pypy.rpython.rmodel import IntegerRepr, inputconst
from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rctypes.rmodel import CTypesRefRepr, CTypesValueRepr
from pypy.rpython.rctypes.rmodel import genreccopy_arrayitem, reccopy, C_ZERO
from pypy.rpython.rctypes.rmodel import unsafe_getfield
from pypy.rpython.rctypes.rprimitive import PrimitiveRepr
from pypy.rpython.rctypes.rpointer import PointerRepr
from pypy.rpython.rctypes.aarray import VarSizedArrayType
from pypy.annotation.model import SomeCTypesObject
from pypy.objspace.flow.model import Constant
from pypy.rlib.objectmodel import keepalive_until_here

ArrayType = type(ARRAY(c_int, 10))


class ArrayRepr(CTypesRefRepr):
    def __init__(self, rtyper, s_array):
        array_ctype = s_array.knowntype
        
        item_ctype = array_ctype._type_
        if isinstance(array_ctype, VarSizedArrayType):
            self.length = None
        else:
            self.length = array_ctype._length_
        
        # Find the repr and low-level type of items from their ctype
        self.r_item = rtyper.getrepr(SomeCTypesObject(item_ctype,
                                                      ownsmemory=False))

        # Here, self.c_data_type == self.ll_type
        if self.length is not None:
            c_data_type = lltype.FixedSizeArray(self.r_item.ll_type,
                                                self.length)
        else:
            c_data_type = lltype.Array(self.r_item.ll_type,
                                       hints={'nolength': True})

        super(ArrayRepr, self).__init__(rtyper, s_array, c_data_type)

    def get_content_keepalive_type(self):
        "An extra array of keepalives, one per item."
        item_keepalive_type = self.r_item.get_content_keepalive_type()
        if not item_keepalive_type:
            return None
        elif self.length is not None:
            return lltype.FixedSizeArray(item_keepalive_type, self.length)
        else:
            raise NotImplementedError("XXX not supported yet: "
                                      "var-sized arrays of pointers")

    def initialize_const(self, p, value):
        for i in range(self.length):
            llitem = self.r_item.convert_const(value[i])
            if isinstance(self.r_item, CTypesRefRepr):
                # ByRef case
                reccopy(llitem.c_data, p.c_data[i])
            else:
                # ByValue case
                p.c_data[i] = llitem.c_data[0]

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        assert self.r_item.ll_type == lltype.Char  # .value: char arrays only
        hop.exception_cannot_occur()
        if self.length == 0:
            return hop.inputconst(lltype.typeOf(emptystr), emptystr)
        else:
            v_box = hop.inputarg(self, 0)
            return hop.gendirectcall(ll_chararrayvalue, v_box)

    def get_c_data_of_item(self, llops, v_array, v_index):
        v_c_array = self.get_c_data(llops, v_array)
        if isinstance(self.r_item, CTypesRefRepr):
            # ByRef case
            return llops.genop('getarraysubstruct', [v_c_array, v_index],
                               lltype.Ptr(self.r_item.c_data_type))
        else:
            # ByValue case
            P = lltype.Ptr(lltype.FixedSizeArray(self.r_item.ll_type, 1))
            v_items = llops.genop('direct_arrayitems', [v_c_array],
                                  resulttype = P)
            if isinstance(v_index, Constant) and v_index.value == 0:
                pass   # skip direct_ptradd
            else:
                v_items = llops.genop('direct_ptradd', [v_items, v_index],
                                      resulttype = P)
            return v_items

    def get_item_value(self, llops, v_array, v_index):
        # ByValue case only
        assert isinstance(self.r_item, CTypesValueRepr)
        v_c_array = self.get_c_data(llops, v_array)
        return llops.genop('getarrayitem', [v_c_array, v_index],
                           resulttype = self.r_item.ll_type)

##    def set_item_value(self, llops, v_array, v_index, v_newvalue):
##        # ByValue case only
##        assert isinstance(self.r_item, CTypesValueRepr)
##        v_c_array = self.get_c_data(llops, v_array)
##        llops.genop('setarrayitem', [v_c_array, v_index, v_newvalue])

    def setitem(self, llops, v_array, v_index, v_item):
        v_newvalue = self.r_item.get_c_data_or_value(llops, v_item)
        # copy the new value (which might be a whole structure)
        v_c_array = self.get_c_data(llops, v_array)
        genreccopy_arrayitem(llops, v_newvalue, v_c_array, v_index)
        # copy the keepalive information too
        v_keepalive_array = self.getkeepalive(llops, v_array)
        if v_keepalive_array is not None:
            v_newkeepalive = self.r_item.getkeepalive(llops, v_item)
            genreccopy_arrayitem(llops, v_newkeepalive,
                                 v_keepalive_array, v_index)

    def initializeitems(self, llops, v_array, items_v):
        for i, v_item in enumerate(items_v):
            c_index = inputconst(lltype.Signed, i)
            self.setitem(llops, v_array, c_index, v_item)


class __extend__(pairtype(ArrayRepr, IntegerRepr)):
    def rtype_getitem((r_array, r_int), hop):
        v_array, v_index = hop.inputargs(r_array, lltype.Signed)
        hop.exception_cannot_occur()
        if isinstance(r_array.r_item, PrimitiveRepr):
            # primitive case (optimization; the below also works in this case)
            # NB. this optimization is invalid for PointerReprs!  See for
            # example:  a[0].contents = ...  to change the first pointer of
            # an array of pointers.
            v_value = r_array.get_item_value(hop.llops, v_array, v_index)
            return r_array.r_item.return_value(hop.llops, v_value)
        else:
            # ByRef case
            v_c_data = r_array.get_c_data_of_item(hop.llops, v_array, v_index)
            return r_array.r_item.return_c_data(hop.llops, v_c_data)

    def rtype_setitem((r_array, r_int), hop):
        v_array, v_index, v_item = hop.inputargs(r_array, lltype.Signed,
                                                 r_array.r_item)
        hop.exception_cannot_occur()
        r_array.setitem(hop.llops, v_array, v_index, v_item)


class __extend__(pairtype(ArrayRepr, AbstractSliceRepr)):
    def rtype_getitem((r_array, r_slic), hop):
        rs = hop.rtyper.type_system.rslice
        hop.exception_cannot_occur()
        if r_slic == rs.startstop_slice_repr:
            # slicing: char array only
            assert r_array.r_item.ll_type == lltype.Char
            if r_array.length == 0:
                return hop.inputconst(lltype.typeOf(emptystr), emptystr)
            v_array, v_slice = hop.inputargs(r_array, rs.startstop_slice_repr)
            return hop.gendirectcall(ll_chararrayslice, v_array, v_slice)
        raise TyperError('getitem does not support slices with %r' % (r_slic,))


class __extend__(pairtype(ArrayRepr, PointerRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # XXX keepalives
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        v_c_array = r_from.get_c_data_of_item(llops, v, C_ZERO)
        r_temp.setvalue(llops, v_owned_box, v_c_array)
        return llops.convertvar(v_owned_box, r_temp, r_to)


def ll_chararrayvalue(box):
    from pypy.rpython.rctypes import rchar_p
    p = unsafe_getfield(box, 'c_data')
    length = rchar_p.ll_strnlen(lltype.direct_arrayitems(p), len(p))
    newstr = lltype.malloc(string_repr.lowleveltype.TO, length)
    newstr.hash = 0
    for i in range(length):
        newstr.chars[i] = p[i]
    keepalive_until_here(box)
    return newstr

def ll_chararrayslice(box, slice):
    from pypy.rpython.rctypes import rchar_p
    p = box.c_data
    start = slice.start
    stop = slice.stop
    length = stop - start
    assert length >= 0
    newstr = lltype.malloc(string_repr.lowleveltype.TO, length)
    newstr.hash = 0
    for i in range(length):
        newstr.chars[i] = p[start+i]
    return newstr
