from pypy.rpython.rctypes.rmodel import CTypesValueRepr, C_ZERO
from pypy.rpython.rctypes.rstringbuf import StringBufRepr
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rctypes.rchar_p import CCharPRepr
from pypy.rpython.lltypesystem import llmemory

class CVoidPRepr(CTypesValueRepr):
    pass  # No operations supported on c_void_p instances so far

class __extend__(pairtype(StringBufRepr, CVoidPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # warning: no keepalives, only for short-lived conversions like
        # in argument passing
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        v_c_array = r_from.get_c_data_of_item(llops, v, C_ZERO)
        v_adr = llops.genop('cast_ptr_to_adr', [v_c_array],
                            resulttype = llmemory.Address)
        r_temp.setvalue(llops, v_owned_box, v_adr)
        return llops.convertvar(v_owned_box, r_temp, r_to)
        # XXX some code duplication above

class __extend__(pairtype(CCharPRepr, CVoidPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        v_ptr = r_from.getvalue(llops, v)
        v_adr = llops.genop('cast_ptr_to_adr', [v_ptr],
                            resulttype = llmemory.Address)
                            
        return r_to.return_value(llops, v_adr)

