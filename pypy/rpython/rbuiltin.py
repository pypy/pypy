from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeBuiltin, SomeObject
from pypy.rpython.lltype import malloc, typeOf, Void, Signed
from pypy.rpython.rtyper import TyperError, peek_at_result_annotation
from pypy.rpython.rtyper import receiveconst, receive, direct_op, convertvar


class __extend__(SomeBuiltin):

    def lowleveltype(s_blt):
        if s_blt.s_self is None:
            assert s_blt.is_constant()
            return Void
        else:
            # methods of a known name are implemented as just their 'self'
            assert s_blt.methodname is not None
            return s_blt.s_self.lowleveltype()

    def rtype_simple_call(s_blt, *args_s):
        if s_blt.s_self is None:
            if not s_blt.is_constant():
                raise TyperError("non-constant built-in")
            bltintyper = BUILTIN_TYPER[s_blt.const]
        else:
            # methods: look up the rtype_method_xxx()
            name = 'rtype_method_' + s_blt.methodname
            bltintyper = getattr(s_blt.s_self, name)
        return bltintyper(*args_s)


class __extend__(pairtype(SomeBuiltin, SomeObject)):

    def rtype_convert_from_to((s_blt, s_to), v):
        if s_blt.s_self is None:
            raise TyperError("conversion requested on a built-in function")
        return convertvar(v, s_blt.s_self, s_to)

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

def rtype_typeOf(s_value):
    s_result = peek_at_result_annotation()
    return receiveconst(Void, s_result.const)


BUILTIN_TYPER = {
    malloc: rtype_malloc,
    typeOf: rtype_typeOf,
    }
