from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython import lltype
from pypy.rpython import rarithmetic
from pypy.rpython.lltype import Void, Signed
from pypy.rpython.rtyper import TyperError
from pypy.rpython.rrange import rtype_builtin_range
from pypy.rpython.rmodel import Repr, TyperError


class __extend__(annmodel.SomeBuiltin):
    def rtyper_makerepr(self, rtyper):
        if self.s_self is None:
            # built-in function case
            if not self.is_constant():
                raise TyperError("non-constant built-in function!")
            return BuiltinFunctionRepr(self.const)
        else:
            # built-in method case
            assert self.methodname is not None
            return BuiltinMethodRepr(rtyper.getrepr(self.s_self),
                                     self.methodname)
    def rtyper_makekey(self):
        key = (getattr(self, 'const', None), self.methodname)
        if self.s_self is not None:
            key += (self.s_self.rtyper_makekey(),)
        return key


class BuiltinFunctionRepr(Repr):
    lowleveltype = Void

    def __init__(self, builtinfunc):
        self.builtinfunc = builtinfunc

    def rtype_simple_call(self, hop):
        try:
            bltintyper = BUILTIN_TYPER[self.builtinfunc]
        except KeyError:
            raise TyperError("don't know about built-in function %r" % (
                self.builtinfunc,))
        hop.r_s_popfirstarg()
        return bltintyper(hop)


class BuiltinMethodRepr(Repr):

    def __init__(self, self_repr, methodname):
        self.self_repr = self_repr
        self.methodname = methodname
        # methods of a known name are implemented as just their 'self'
        self.lowleveltype = self_repr.lowleveltype

    def rtype_simple_call(self, hop):
        # methods: look up the rtype_method_xxx()
        name = 'rtype_method_' + self.methodname
        try:
            bltintyper = getattr(self.self_repr, name)
        except AttributeError:
            raise TyperError("missing %s.%s" % (
                self.self_repr.__class__.__name__, name))
        # hack based on the fact that 'lowleveltype == self_repr.lowleveltype'
        assert hop.args_r[0] is self
        hop.args_r[0] = self.self_repr
        return bltintyper(hop)


##class __extend__(pairtype(SomeBuiltin, SomeObject)):

##    def rtype_convert_from_to((s_blt, s_to), v, llops):
##        if s_blt.s_self is None:
##            raise TyperError("conversion requested on a built-in function")
##        return llops.convertvar(v, s_blt.s_self, s_to)

# ____________________________________________________________

def rtype_builtin_bool(hop):
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_is_true(hop)

def rtype_builtin_int(hop):
    if isinstance(hop.args_s[0], annmodel.SomeString):
        raise TyperError('int("string") not supported')
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_int(hop)

def rtype_builtin_float(hop):
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_float(hop)

#def rtype_builtin_range(hop): see rrange.py

def rtype_intmask(hop):
    vlist = hop.inputargs(Signed)
    return vlist[0]


# collect all functions
import __builtin__
BUILTIN_TYPER = {}
for name, value in globals().items():
    if name.startswith('rtype_builtin_'):
        original = getattr(__builtin__, name[14:])
        BUILTIN_TYPER[original] = value

# annotation of low-level types

def rtype_malloc(hop):
    assert hop.args_s[0].is_constant()
    if hop.nb_args == 1:
        vlist = hop.inputargs(Void)
        return hop.genop('malloc', vlist,
                         resulttype = hop.r_result.lowleveltype)
    else:
        vlist = hop.inputargs(Void, Signed)
        return hop.genop('malloc_varsize', vlist,
                         resulttype = hop.r_result.lowleveltype)

def rtype_const_result(hop):
    return hop.inputconst(Void, hop.s_result.const)


BUILTIN_TYPER[lltype.malloc] = rtype_malloc
BUILTIN_TYPER[lltype.typeOf] = rtype_const_result
BUILTIN_TYPER[lltype.nullptr] = rtype_const_result
BUILTIN_TYPER[rarithmetic.intmask] = rtype_intmask
