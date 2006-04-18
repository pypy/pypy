from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr, inputconst
from pypy.rpython.rctypes.rmodel import CTypesRefRepr
from pypy.objspace.flow.model import Constant


class StringBufRepr(CTypesRefRepr):

    def rtype_len(self, hop):
        [v_stringbuf] = hop.inputargs(self)
        v_array = self.get_c_data(hop.llops, v_stringbuf)
        return hop.genop('getarraysize', [v_array],
                         resulttype = lltype.Signed)

    def rtype_getattr(self, hop):
        from pypy.rpython.rctypes.rarray import ll_chararrayvalue
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_box = hop.inputarg(self, 0)
        return hop.gendirectcall(ll_chararrayvalue, v_box)

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
        return hop.genop('getarrayitem', [v_array, v_index],
                         resulttype = lltype.Char)

    def rtype_setitem((r_stringbuf, r_int), hop):
        v_stringbuf, v_index, v_item = hop.inputargs(r_stringbuf,
                                                     lltype.Signed,
                                                     lltype.Char)
        v_array = r_stringbuf.get_c_data(hop.llops, v_stringbuf)
        hop.genop('setarrayitem', [v_array, v_index, v_item])


STRBUFTYPE = lltype.Array(lltype.Char)
