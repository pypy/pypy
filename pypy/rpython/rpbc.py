import types
from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomePBC
from pypy.rpython.lltype import typeOf
from pypy.rpython import rclass


class __extend__(SomePBC):

    def rtype_getattr(_, hop):
        attr = hop.args_s[1].const
        if hop.s_result.is_constant():
            return hop.inputconst(hop.s_result, hop.s_result.const)
        else:
            NotImplementedYet

    def rtype_simple_call(_, hop):
        s_func = hop.s_popfirstarg()
        if not s_func.is_constant():
            NotImplementedYet
        func = s_func.const
        if isinstance(func, types.FunctionType):
            # XXX hackish
            f = hop.rtyper.getfunctionptr(func)
            FUNCPTR = typeOf(f)
            args_v = hop.inputargs(*FUNCPTR.TO.ARGS)
            c = hop.inputconst(FUNCPTR, f)
            return hop.genop('direct_call', [c] + args_v,
                             resulttype = FUNCPTR.TO.RESULT)
        elif isinstance(func, (types.ClassType, type)):
            return rclass.rtype_new_instance(s_func, hop)
