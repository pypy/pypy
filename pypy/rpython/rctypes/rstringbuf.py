from pypy.rpython.lltypesystem import lltype
from pypy.tool.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr, inputconst
from pypy.rpython.rctypes.rmodel import CTypesRefRepr
from pypy.objspace.flow.model import Constant
from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.rpython.error import TyperError

class StringBufRepr(CTypesRefRepr):

    def rtype_len(self, hop):
        [v_stringbuf] = hop.inputargs(self)
        v_array = self.get_c_data(hop.llops, v_stringbuf)
        return hop.genop('getarraysize', [v_array],
                         resulttype = lltype.Signed)

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        v_box = hop.inputarg(self, 0)
        hop.exception_cannot_occur()
        if s_attr.const == 'value':
            from pypy.rpython.rctypes.rarray import ll_chararrayvalue
            return hop.gendirectcall(ll_chararrayvalue, v_box)
        elif s_attr.const == 'raw':
            return hop.gendirectcall(ll_stringbufraw, v_box)
        else:
            raise TyperError("StringBufRepr has no attribute %r" % (
                s_attr.const,))

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const in ('value', 'raw')
        v_box, v_attr, v_value = hop.inputargs(self, lltype.Void, string_repr)
        hop.gendirectcall(ll_stringbuf_setvalue_from_string, v_box, v_value)

    def get_c_data_of_item(self, llops, v_stringbuf, v_index):
        v_array = self.get_c_data(llops, v_stringbuf)
        v_char_p = llops.genop('direct_arrayitems', [v_array],
                               resulttype = ONE_CHAR_PTR)
        if isinstance(v_index, Constant) and v_index.value == 0:
            pass   # skip direct_ptradd
        else:
            v_char_p = llops.genop('direct_ptradd', [v_char_p, v_index],
                                   resulttype = ONE_CHAR_PTR)
        return v_char_p


ONE_CHAR_PTR = lltype.Ptr(lltype.FixedSizeArray(lltype.Char, 1))


class __extend__(pairtype(StringBufRepr, IntegerRepr)):
    def rtype_getitem((r_stringbuf, r_int), hop):
        v_stringbuf, v_index = hop.inputargs(r_stringbuf, lltype.Signed)
        v_array = r_stringbuf.get_c_data(hop.llops, v_stringbuf)
        hop.exception_cannot_occur()
        return hop.genop('getarrayitem', [v_array, v_index],
                         resulttype = lltype.Char)

    def rtype_setitem((r_stringbuf, r_int), hop):
        v_stringbuf, v_index, v_item = hop.inputargs(r_stringbuf,
                                                     lltype.Signed,
                                                     lltype.Char)
        v_array = r_stringbuf.get_c_data(hop.llops, v_stringbuf)
        hop.exception_cannot_occur()
        hop.genop('setarrayitem', [v_array, v_index, v_item])

class __extend__(pairtype(StringBufRepr, AbstractSliceRepr)):
    def rtype_getitem((r_stringbuf, r_slice), hop):
        rs = r_stringbuf.rtyper.type_system.rslice
        if r_slice == rs.startonly_slice_repr:
            v_stringbuf, v_start = hop.inputargs(r_stringbuf, rs.startonly_slice_repr)
            v_array = r_stringbuf.get_c_data(hop.llops, v_stringbuf)
            return hop.gendirectcall(ll_slice_startonly, v_array, v_start)
        if r_slice == rs.startstop_slice_repr:
            v_stringbuf, v_slice = hop.inputargs(r_stringbuf, rs.startstop_slice_repr)
            v_array = r_stringbuf.get_c_data(hop.llops, v_stringbuf)
            return hop.gendirectcall(ll_slice, v_array, v_slice)
        raise TyperError('getitem does not support slices with %r' % (r_slice,))

def ll_slice_startonly(sbuf, start):
    return ll_slice_start_stop(sbuf, start, len(sbuf))
    
def ll_slice(sbuf, slice):
    return ll_slice_start_stop(sbuf, slice.start, slice.stop)

def ll_slice_start_stop(sbuf, start, stop):
    length = len(sbuf)
    if start < 0:
        start = length + start
    if start < 0:
        start = 0
    if stop < 0:
        stop = length + stop
    if stop < 0:
        stop = 0
    if stop > length:
        stop = length
    if start > stop:
        start = stop
    newlength = stop - start
    newstr = lltype.malloc(string_repr.lowleveltype.TO, newlength)
    newstr.hash = 0
    for i in range(newlength):
        newstr.chars[i] = sbuf[start + i]
    return newstr


def ll_stringbuf_setvalue_from_string(box, s):
    # Copy the string into the stringbuf.  In ctypes the final \x00 is
    # copied unless the string has exactly the same size as the stringbuf.
    # We do the same, but unlike ctypes don't raise ValueError if the
    # string is longer than the stringbuf; we just truncate instead.
    # There is no support for setattr raising exceptions in RPython so far.
    p = box.c_data
    n = min(len(s.chars) + 1, len(p))
    for i in range(n):
        p[i] = s.chars[i]

def ll_stringbufraw(box):
    p = box.c_data
    length = len(p)
    newstr = lltype.malloc(string_repr.lowleveltype.TO, length)
    newstr.hash = 0
    for i in range(length):
        newstr.chars[i] = p[i]
    return newstr

STRBUFTYPE = lltype.Array(lltype.Char)
