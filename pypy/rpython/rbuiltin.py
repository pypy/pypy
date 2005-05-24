from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeBuiltin
from pypy.rpython.lltype import malloc, Void, Signed
from pypy.rpython.rtyper import TyperError, peek_at_result_annotation
from pypy.rpython.rtyper import receiveconst, receive, direct_op


class __extend__(SomeBuiltin):

    def rtype_simple_call(s_blt, *args_s):
        if not s_blt.is_constant():
            raise TyperError("non-constant built-in")
        bltintyper = BUILTIN_TYPER[s_blt.const]
        return bltintyper(*args_s)

# ____________________________________________________________

def rtype_malloc(s_pbc_type, s_varlength=None):
    assert s_pbc_type.is_constant()
    v_type = receiveconst(Void, s_pbc_type.const)
    s_result = peek_at_result_annotation()
    if s_varlength is None:
        return direct_op('malloc', [v_type],
                         resulttype = s_result.lowleveltype())
    else:
        v_varlength = receive(Signed, arg=2)   # NOTE, arg=0 is the s_blt above
        return direct_op('malloc_varsize', [v_type, v_varlength],
                         resulttype = s_result.lowleveltype())


BUILTIN_TYPER = {
    malloc: rtype_malloc,
    }
