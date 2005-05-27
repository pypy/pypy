import types
from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomePBC
from pypy.rpython.lltype import typeOf
from pypy.rpython.rtyper import TLS, receive, receiveconst, direct_op
from pypy.rpython.rtyper import peek_at_result_annotation


class __extend__(SomePBC):

    def rtype_getattr(s_pbc, s_attr):
        attr = s_attr.const
        s_result = peek_at_result_annotation()
        if s_result.is_constant():
            return receiveconst(s_result, s_result.const)
        else:
            NotImplementedYet

    def rtype_simple_call(s_pbc, *args_s):
        if not s_pbc.is_constant():
            NotImplementedYet
        func = s_pbc.const
        if not isinstance(func, types.FunctionType):
            NotImplementedYet
        # XXX hackish
        f = TLS.rtyper.getfunctionptr(func)
        FUNCPTR = typeOf(f)
        args_v = [receive(FUNCPTR.TO.ARGS[i], arg=i+1)
                  for i in range(len(args_s))]
        c = receiveconst(FUNCPTR, f)
        return direct_op('direct_call', [c] + args_v,
                         resulttype = FUNCPTR.TO.RESULT)
