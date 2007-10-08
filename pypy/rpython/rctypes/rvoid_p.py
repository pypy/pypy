from pypy.rpython.rctypes.rmodel import CTypesValueRepr, C_ZERO
from pypy.rpython.rctypes.rmodel import unsafe_getfield
from pypy.rpython.rctypes.rstringbuf import StringBufRepr
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rstr import AbstractStringRepr
from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.rpython.rctypes.rchar_p import CCharPRepr
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rctypes.rpointer import PointerRepr
from pypy.rpython.rctypes.rarray import ArrayRepr

class CVoidPRepr(CTypesValueRepr):
    def convert_const(self, value):
        if isinstance(value, self.ctype):
            return super(CVoidPRepr, self).convert_const(value)
        raise NotImplementedError("XXX constant pointer passed to void* arg")

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_box = hop.inputarg(self, 0)
        v_c_adr = self.getvalue(hop.llops, v_box)
        hop.exception_cannot_occur()
        return hop.genop('cast_adr_to_int', [v_c_adr],
                         resulttype = lltype.Signed)


class __extend__(pairtype(CCharPRepr, CVoidPRepr),
                 pairtype(PointerRepr, CVoidPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        v_ptr = r_from.getvalue(llops, v)
        v_adr = llops.genop('cast_ptr_to_adr', [v_ptr],
                            resulttype = llmemory.Address)
                            
        return r_to.return_value(llops, v_adr)

class __extend__(pairtype(StringBufRepr, CVoidPRepr),
                 pairtype(ArrayRepr, CVoidPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        v_ptr = r_from.get_c_data_of_item(llops, v, C_ZERO)
        v_adr = llops.genop('cast_ptr_to_adr', [v_ptr],
                            resulttype = llmemory.Address)
                            
        return r_to.return_value(llops, v_adr)

class __extend__(pairtype(AbstractStringRepr, CVoidPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # warning: no keepalives, only for short-lived conversions like
        # in argument passing
        # r_from could be char_repr: first convert it to string_repr
        v = llops.convertvar(v, r_from, string_repr)
        v_adr = llops.gendirectcall(ll_string2addr, v)
        return r_to.return_value(llops, v_adr)

def ll_string2addr(s):
    if s:
        ptr = lltype.direct_arrayitems(unsafe_getfield(s, 'chars'))
        return llmemory.cast_ptr_to_adr(ptr)
    else:
        return llmemory.NULL
