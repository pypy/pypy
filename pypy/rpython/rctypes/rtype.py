from pypy.objspace.flow.model import Constant
from pypy.tool.pairtype import pairtype
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.error import TyperError
from pypy.rpython.rbuiltin import BuiltinFunctionRepr


class TypeRepr(BuiltinFunctionRepr):

    def __init__(self, s_ctype):
        assert s_ctype.s_self is None
        if not s_ctype.is_constant():
            raise TyperError("non-constant ctypes type object")
        ctype = s_ctype.const
        BuiltinFunctionRepr.__init__(self, ctype)


class __extend__(pairtype(TypeRepr, IntegerRepr)):

    def rtype_mul((r_ctype, r_int), hop):
        v_ctype, v_repeatcount = hop.inputargs(r_ctype, lltype.Signed)
        assert isinstance(v_ctype, Constant)
        return v_repeatcount


class VarSizedTypeRepr(Repr):
    """Repr of the var-sized array type built at runtime as 'ctype*int'.
    The ctype must be a real constant ctype, so the var-sized type can
    be represented as just the runtime length.
    """
    lowleveltype = lltype.Signed

    def rtype_simple_call(self, hop):
        r_array = hop.r_result
        args_r = [self] + [r_array.r_item] * (hop.nb_args-1)
        args_v = hop.inputargs(*args_r)
        v_repeatcount = args_v[0]
        hop.exception_cannot_occur()
        v_result = r_array.allocate_instance_varsize(hop.llops, v_repeatcount)
        r_array.initializeitems(hop.llops, v_result, args_v[1:])
        return v_result
