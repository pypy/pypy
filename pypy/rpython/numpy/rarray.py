from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.rrange import AbstractRangeRepr
from pypy.rpython.rint import IntegerRepr
from pypy.rpython.rlist import AbstractBaseListRepr
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lltype import \
     GcArray, GcStruct, Signed, Ptr, Unsigned, malloc, Void
from pypy.annotation.model import SomeObject, SomeInteger
from pypy.rpython.numpy.aarray import SomeArray
from pypy.annotation.pairtype import pairtype


class ArrayRepr(Repr):
    def __init__(self, rtyper, s_array):
        self.s_value = s_array.get_item_type()
        self.item_repr = rtyper.getrepr(self.s_value)
        ITEM = self.item_repr.lowleveltype
        ITEMARRAY = GcArray(ITEM)
        SIZEARRAY = GcArray(Signed)
        self.ARRAY = Ptr(
            GcStruct("array",
                ("data", Ptr(ITEMARRAY)), # pointer to raw data buffer 
                ("nd", Signed), # number of dimensions, also called ndim
                ("dimensions", Ptr(SIZEARRAY)), # size in each dimension
                ("strides", Ptr(SIZEARRAY)), # bytes to jump to get to the
                                             # next element in each dimension 
            ))
        self.lowleveltype = self.ARRAY

    def allocate_instance(self, llops, v_array):
        c1 = inputconst(lltype.Void, self.lowleveltype.TO) 
        return llops.gendirectcall(ll_allocate, c1, v_array)

    def rtype_method_transpose(self, hop):
        [v_self] = hop.inputargs(self)
        cARRAY = hop.inputconst(Void, hop.r_result.ARRAY.TO)
        return hop.gendirectcall(ll_transpose, cARRAY, v_self)

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            s_obj = hop.args_s[0]
            vobj, vattr = hop.inputargs(self, Void)
            llops = hop.llops
            if attr == 'ndim':
                cname = inputconst(Void, 'nd')
                return llops.genop('getfield', [vobj, cname], resulttype=Signed)
        return Repr.rtype_getattr(self, hop)


class __extend__(SomeArray):
    def rtyper_makerepr(self, rtyper):
        return ArrayRepr( rtyper, self )

    def rtyper_makekey(self):
        return self.__class__, self.knowntype


class __extend__(pairtype(ArrayRepr, ArrayRepr)):
    def rtype_add((r_arr1,r_arr2), hop):
        v_arr1, v_arr2 = hop.inputargs(r_arr1, r_arr2)
        cARRAY = hop.inputconst(Void, hop.r_result.ARRAY.TO)
        return hop.gendirectcall(ll_add, cARRAY, v_arr1, v_arr2)


class __extend__(pairtype(ArrayRepr, IntegerRepr)):
    def rtype_setitem((r_arr,r_int), hop):
        v_array, v_index, v_item = hop.inputargs(r_arr, Signed, r_arr.item_repr)
        return hop.gendirectcall(ll_setitem, v_array, v_index, v_item)

    def rtype_getitem((r_arr,r_int), hop):
        v_array, v_index = hop.inputargs(r_arr, Signed)
        return hop.gendirectcall(ll_getitem, v_array, v_index)

class __extend__(pairtype(AbstractBaseListRepr, ArrayRepr)):
    def convert_from_to((r_lst, r_arr), v, llops):
        if r_lst.listitem is None:
            return NotImplemented
        if r_lst.item_repr != r_arr.item_repr:
            return NotImplemented
        c1 = inputconst(lltype.Void, r_arr.lowleveltype.TO) 
        return llops.gendirectcall(ll_build_array, c1, v)

class __extend__(pairtype(AbstractRangeRepr, ArrayRepr)):
    def convert_from_to((r_rng, r_arr), v, llops):
        c1 = inputconst(lltype.Void, r_arr.lowleveltype.TO) 
        return llops.gendirectcall(ll_build_array, c1, v)

def ll_build_array(ARRAY, lst):
    size = lst.ll_length()
    array = malloc(ARRAY)
    data = array.data = malloc(ARRAY.data.TO, size)
    i = 0
    while i < size:
        data[i] = lst.ll_getitem_fast(i)
        i += 1
    array.nd = 1
    return array

def ll_allocate(ARRAY, array):
    new_array = malloc(ARRAY)
    new_array.data = array.data # alias data
    new_array.nd = array.nd
    return new_array

def ll_setitem(l, index, item):
    l.data[index] = item

def ll_getitem(l, index):
    return l.data[index]

def ll_add(ARRAY, a1, a2):
    size = len(a1.data)
    if size != len(a2.data):
        raise ValueError
    array = malloc(ARRAY)
    array.data = malloc(ARRAY.data.TO, size)
    i = 0
    while i < size:
        array.data[i] = a1.data[i] + a2.data[i]
        i += 1
    return array

def ll_transpose(ARRAY, a1):
    a2 = ll_allocate(ARRAY, a1)
    # XX do something to a2
    return a2
    


