from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeBuiltin, SomeObject
from pypy.rpython.lltype import malloc, typeOf, Void, Signed
from pypy.rpython.rtyper import TyperError


class __extend__(SomeBuiltin):

    def lowleveltype(s_blt):
        if s_blt.s_self is None:
            assert s_blt.is_constant()
            return Void
        else:
            # methods of a known name are implemented as just their 'self'
            assert s_blt.methodname is not None
            return s_blt.s_self.lowleveltype()

    def rtype_simple_call(s_blt, hop):
        if s_blt.s_self is None:
            if not s_blt.is_constant():
                raise TyperError("non-constant built-in")
            bltintyper = BUILTIN_TYPER[s_blt.const]
            hop.s_popfirstarg()
        else:
            # methods: look up the rtype_method_xxx()
            name = 'rtype_method_' + s_blt.methodname
            bltintyper = getattr(s_blt.s_self, name)
        return bltintyper(hop)


class __extend__(pairtype(SomeBuiltin, SomeObject)):

    def rtype_convert_from_to((s_blt, s_to), v, llops):
        if s_blt.s_self is None:
            raise TyperError("conversion requested on a built-in function")
        return llops.convertvar(v, s_blt.s_self, s_to)

# ____________________________________________________________

def rtype_malloc(hop):
    assert hop.args_s[0].is_constant()
    if hop.nb_args == 1:
        vlist = hop.inputargs(Void)
        return hop.genop('malloc', vlist,
                         resulttype = hop.s_result.lowleveltype())
    else:
        vlist = hop.inputargs(Void, Signed)
        return hop.genop('malloc_varsize', vlist,
                         resulttype = hop.s_result.lowleveltype())

def rtype_typeOf(hop):
    return hop.inputconst(Void, hop.s_result.const)


BUILTIN_TYPER = {
    malloc: rtype_malloc,
    typeOf: rtype_typeOf,
    }
