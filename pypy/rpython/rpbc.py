import types
import sys
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Void, Bool, nullptr
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython import rclass
from pypy.rpython import robject

from pypy.rpython import callparse

class __extend__(annmodel.SomePBC):
    def rtyper_makerepr(self, rtyper):
        # for now, we require that the PBC fits neatly into one of the Repr
        # categories below, and doesn't for example mix functions, classes
        # and methods.
        call_families = rtyper.annotator.getpbccallfamilies()
        userclasses = rtyper.annotator.getuserclasses()
        access_sets = rtyper.annotator.getpbcaccesssets()
        choices = {}
        for x, classdef in self.prebuiltinstances.items():
            cdefflag = isclassdef(classdef)
            if not cdefflag:
                classdef = None

            # consider unbound methods as plain functions
            if isinstance(x, types.MethodType) and x.im_self is None:
                x = x.im_func

            if cdefflag:
                # methods of a run-time instance
                if not isinstance(x, types.FunctionType):
                    raise TyperError("%r appears to be a method bound to %r, "
                                     "but it is not a function" % (
                        x, classdef))
                choice = rtyper.type_system.rpbc.MethodsPBCRepr

            elif x is None:
                continue    # skipped, a None is allowed implicitely anywhere

            elif isinstance(x, (type, types.ClassType)):
                # classes
                if x in userclasses:
                    # user classes
                    choice = rtyper.type_system.rpbc.ClassesPBCRepr
                elif type(x) is type and x.__module__ in sys.builtin_module_names:
                    # special case for built-in types, seen in faking
                    choice = getPyObjRepr
                else:
                    # classes that are never instantiated => consider them
                    # as plain frozen objects
                    choice = getFrozenPBCRepr

            elif (classdef, x) in call_families:
                # other kind of callable
                if isinstance(x, types.FunctionType):
                    # function
                    choice = FunctionsPBCRepr
                elif isinstance(x, types.MethodType):
                    # prebuilt bound method
                    choice = rtyper.type_system.rpbc.MethodOfFrozenPBCRepr
                else:
                    raise TyperError("don't know about callable %r" % (x,))

            elif isinstance(x, builtin_descriptor_type):
                # strange built-in functions, method objects, etc. from fake.py
                choice = getPyObjRepr

            else:
                # otherwise, just assume it's a plain frozen object
                choice = getFrozenPBCRepr

            choices[choice] = True

        if len(choices) > 1:
            raise TyperError("mixed kinds of PBC in the set %r" % (
                self.prebuiltinstances,))
        if len(choices) < 1:
            return none_frozen_pbc_repr    # prebuiltinstances == {None: True}
        reprcls, = choices
        return reprcls(rtyper, self)

    def rtyper_makekey(self):
        lst = self.prebuiltinstances.items()
        lst.sort()
        return tuple([self.__class__]+lst)

builtin_descriptor_type = (
    type(len),                             # type 'builtin_function_or_method'
    type(list.append),                     # type 'method_descriptor'
    type(type(None).__repr__),             # type 'wrapper_descriptor'
    type(type.__dict__['__dict__']),       # type 'getset_descriptor'
    type(type.__dict__['__basicsize__']),  # type 'member_descriptor'
    )

# ____________________________________________________________

class MultiplePBCRepr(Repr):
    """Base class for PBCReprs of multiple PBCs that can include None
    (represented as a NULL pointer)."""
    def rtype_is_true(self, hop):
        if hop.s_result.is_constant():
            assert hop.s_result.const is True    # custom __nonzero__ on PBCs?
            return hop.inputconst(Bool, hop.s_result.const)
        else:
            return hop.rtyper.type_system.check_null(self, hop)

class FunctionsPBCRepr(MultiplePBCRepr):
    """Representation selected for a PBC of function(s)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        self._function_signatures = None
        if len(s_pbc.prebuiltinstances) == 1:
            # a single function
            self.lowleveltype = Void
        else:
            signatures = self.function_signatures().values()
            sig0 = signatures[0]
            for sig1 in signatures[1:]:
                assert typeOf(sig0[0]) == typeOf(sig1[0])  # XXX not implemented
                assert sig0[1:] == sig1[1:]                # XXX not implemented
            self.lowleveltype = typeOf(sig0[0])

    def get_s_callable(self):
        return self.s_pbc

    def get_r_implfunc(self):
        return self, 0

    def get_signature(self):
        return self.function_signatures().itervalues().next()

    def get_args_ret_s(self):
        f, _, _ = self.get_signature()
        graph = self.rtyper.type_system_deref(f).graph
        rtyper = self.rtyper
        return [rtyper.binding(arg) for arg in graph.getargs()], rtyper.binding(graph.getreturnvar())

    def function_signatures(self):
        if self._function_signatures is None:
            self._function_signatures = {}
            for func in self.s_pbc.prebuiltinstances:
                if func is not None:
                    self._function_signatures[func] = getsignature(self.rtyper,
                                                                   func)
            assert self._function_signatures
        return self._function_signatures

    def convert_const(self, value):
        if value is None:
            return nullptr(self.lowleveltype.TO)
        if isinstance(value, types.MethodType) and value.im_self is None:
            value = value.im_func   # unbound method -> bare function
        if value not in self.function_signatures():
            raise TyperError("%r not in %r" % (value,
                                               self.s_pbc.prebuiltinstances))
        f, rinputs, rresult = self.function_signatures()[value]
        return f

    def rtype_simple_call(self, hop):
        f, rinputs, rresult = self.function_signatures().itervalues().next()

        if getattr(self.rtyper.type_system_deref(f).graph, 'normalized_for_calls', False):
            # should not have an argument count mismatch
            assert len(rinputs) == hop.nb_args-1, "normalization bug"
            vlist = hop.inputargs(self, *rinputs)
        else:
            # if not normalized, should be a call to a known function
            # or to functions all with same signature
            funcs = self.function_signatures().keys()
            assert samesig(funcs), "normalization bug"
            func = funcs[0]
            vlist = [hop.inputarg(self, arg=0)]
            vlist += callparse.callparse('simple_call', func, rinputs, hop)

        return self.call(hop, f, vlist, rresult)

    def call(self, hop, f, vlist, rresult):
        if self.lowleveltype is Void:
            assert len(self.function_signatures()) == 1
            vlist[0] = hop.inputconst(typeOf(f), f)
        hop.exception_is_here()
        v = hop.genop('direct_call', vlist, resulttype = rresult)
        return hop.llops.convertvar(v, rresult, hop.r_result)

    def rtype_call_args(self, hop):
        f, rinputs, rresult = self.function_signatures().itervalues().next()
        # the function arguments may have been normalized by normalizecalls()
        # already
        if getattr(self.rtyper.type_system_deref(f).graph, 'normalized_for_calls', False):
            vlist = hop.inputargs(self, Void, *rinputs)
            vlist = vlist[:1] + vlist[2:]
        else:
            # if not normalized, should be a call to a known function
            # or to functions all with same signature
            funcs = self.function_signatures().keys()
            assert samesig(funcs), "normalization bug"
            func = funcs[0]
            vlist = [hop.inputarg(self, arg=0)] 
            vlist += callparse.callparse('call_args', func, rinputs, hop)

        return self.call(hop, f, vlist, rresult)

class __extend__(pairtype(FunctionsPBCRepr, FunctionsPBCRepr)):
        def convert_from_to((r_fpbc1, r_fpbc2), v, llops):
            # this check makes sense because both source and dest repr are FunctionsPBCRepr
            if r_fpbc1.lowleveltype == r_fpbc2.lowleveltype:
                return v
            if r_fpbc1.lowleveltype is Void:
                return inputconst(r_fpbc2, r_fpbc1.s_pbc.const)
            return NotImplemented

def getPyObjRepr(rtyper, s_pbc):
    return robject.pyobj_repr

def get_access_set(rtyper, pbc):
    access_sets = rtyper.annotator.getpbcaccesssets()
    try:
        return access_sets[pbc]
    except KeyError:
        return None    

def getFrozenPBCRepr(rtyper, s_pbc):
    if len(s_pbc.prebuiltinstances) <= 1:
        #if s_pbc.const is None:   -- take care of by rtyper_makerepr() above
        #    return none_frozen_pbc_repr
        return SingleFrozenPBCRepr(s_pbc.prebuiltinstances.keys()[0])
    else:
        pbcs = [pbc for pbc in s_pbc.prebuiltinstances.keys()
                    if pbc is not None]
        access = get_access_set(rtyper, pbcs[0])
        for obj in pbcs[1:]:
            access1 = get_access_set(rtyper, obj)
            assert access1 is access       # XXX not implemented
        try:
            return rtyper.pbc_reprs[access]
        except KeyError:
            result = rtyper.type_system.rpbc.MultipleFrozenPBCRepr(rtyper, access)
            rtyper.pbc_reprs[access] = result
            rtyper.add_pendingsetup(result) 
            return result


class SingleFrozenPBCRepr(Repr):
    """Representation selected for a single non-callable pre-built constant."""
    lowleveltype = Void

    def __init__(self, value):
        self.value = value

    def rtype_getattr(_, hop):
        if not hop.s_result.is_constant():
            raise TyperError("getattr on a constant PBC returns a non-constant")
        return hop.inputconst(hop.r_result, hop.s_result.const)

# __ None ____________________________________________________
class NoneFrozenPBCRepr(SingleFrozenPBCRepr):
    
    def rtype_is_true(self, hop):
        return Constant(False, Bool)

none_frozen_pbc_repr = NoneFrozenPBCRepr(None)


class __extend__(pairtype(Repr, NoneFrozenPBCRepr)):

    def convert_from_to((r_from, _), v, llops):
        return inputconst(Void, None)
    
    def rtype_is_((robj1, rnone2), hop):
        return hop.rtyper.type_system.rpbc.rtype_is_None(robj1, rnone2, hop)

class __extend__(pairtype(NoneFrozenPBCRepr, Repr)):

    def convert_from_to((_, r_to), v, llops):
        return inputconst(r_to, None)

    def rtype_is_((rnone1, robj2), hop):
        return hop.rtyper.type_system.rpbc.rtype_is_None(
                                                robj2, rnone1, hop, pos=1)
        
class __extend__(pairtype(NoneFrozenPBCRepr, robject.PyObjRepr)):

    def convert_from_to(_, v, llops):
        return inputconst(robject.pyobj_repr, None)

# ____________________________________________________________

class AbstractClassesPBCRepr(Repr):
    """Representation selected for a PBC of class(es)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        if None in s_pbc.prebuiltinstances:
            raise TyperError("unsupported: variable of type "
                             "class-pointer or None")
        if s_pbc.is_constant():
            self.lowleveltype = Void
        else:
            self.lowleveltype = rtyper.type_system.rclass.CLASSTYPE
        self._access_set = None
        self._class_repr = None

    def get_access_set(self):
        if self._access_set is None:
            access_sets = self.rtyper.annotator.getpbcaccesssets()
            classes = self.s_pbc.prebuiltinstances.keys()
            _, _, access = access_sets.find(classes[0])
            for obj in classes[1:]:
                _, _, access1 = access_sets.find(obj)
                assert access1 is access       # XXX not implemented
            commonbase = access.commonbase
            self._class_repr = rclass.getclassrepr(self.rtyper, commonbase)
            self._access_set = access
        return self._access_set

    def get_class_repr(self):
        self.get_access_set()
        return self._class_repr

    def convert_const(self, cls):
        if cls not in self.s_pbc.prebuiltinstances:
            raise TyperError("%r not in %r" % (cls, self))
        if self.lowleveltype is Void:
            return cls
        return rclass.get_type_repr(self.rtyper).convert_const(cls)

    def rtype_getattr(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        else:
            attr = hop.args_s[1].const
            vcls, vattr = hop.inputargs(self, Void)
            return self.getfield(vcls, attr, hop.llops)

    def getfield(self, vcls, attr, llops):
        access_set = self.get_access_set()
        class_repr = self.get_class_repr()
        return class_repr.getpbcfield(vcls, access_set, attr, llops)

class __extend__(pairtype(AbstractClassesPBCRepr, rclass.AbstractClassRepr)):
    def convert_from_to((r_clspbc, r_cls), v, llops):
        if r_cls.lowleveltype != r_clspbc.lowleveltype:
            return NotImplemented   # good enough for now
        return v

class __extend__(pairtype(AbstractClassesPBCRepr, AbstractClassesPBCRepr)):
    def convert_from_to((r_clspbc1, r_clspbc2), v, llops):
        # this check makes sense because both source and dest repr are ClassesPBCRepr
        if r_clspbc1.lowleveltype == r_clspbc2.lowleveltype:
            return v
        if r_clspbc1.lowleveltype is Void:
            return inputconst(r_clspbc2, r_clspbc1.s_pbc.const)
        return NotImplemented

class AbstractMethodsPBCRepr(Repr):
    """Representation selected for a PBC of the form {func: classdef...}.
    It assumes that all the methods come from the same name in a base
    classdef."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        if None in s_pbc.prebuiltinstances:
            raise TyperError("unsupported: variable of type "
                             "bound-method-object or None")
        basedef = commonbase(s_pbc.prebuiltinstances.values())
        for classdef1, name in allattributenames(basedef):
            # don't trust the func.func_names and see if this 'name' would be
            # the one under which we can find all these methods
            for func, classdef in s_pbc.prebuiltinstances.items():
                try:
                    if func != getattr(classdef.cls, name).im_func:
                        break
                except AttributeError:
                    break
            else:
                # yes!
                self.methodname = name
                self.classdef = classdef1   # where the Attribute is defined
                break
        else:
            raise TyperError("cannot find a unique name under which the "
                             "methods can be found: %r" % (
                s_pbc.prebuiltinstances,))
        # the low-level representation is just the bound 'self' argument.
        self.s_im_self = annmodel.SomeInstance(self.classdef)
        self.r_im_self = rclass.getinstancerepr(rtyper, self.classdef)
        self.lowleveltype = self.r_im_self.lowleveltype

    def convert_const(self, method):
        if getattr(method, 'im_func', None) is None:
            raise TyperError("not a bound method: %r" % method)
        return self.r_im_self.convert_const(method.im_self)

    def get_r_implfunc(self):
        r_class = self.r_im_self.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        return r_func, 1

    def get_s_callable(self):
        return self.s_pbc

    def get_method_from_instance(self, r_inst, v_inst, llops):
        # The 'self' might have to be cast to a parent class
        # (as shown for example in test_rclass/test_method_both_A_and_B)
        return llops.convertvar(v_inst, r_inst, self.r_im_self)

# ____________________________________________________________

def getsignature(rtyper, func):
    f = rtyper.getcallable(func)
    graph = rtyper.type_system_deref(f).graph
    rinputs = [rtyper.bindingrepr(v) for v in graph.getargs()]
    if graph.getreturnvar() in rtyper.annotator.bindings:
        rresult = rtyper.bindingrepr(graph.getreturnvar())
    else:
        rresult = Void
    return f, rinputs, rresult

def samesig(funcs):
    import inspect
    argspec = inspect.getargspec(funcs[0])
    for func in funcs:
        if inspect.getargspec(func) != argspec:
            return False
    return True

# ____________________________________________________________

def commonbase(classdefs):
    result = classdefs[0]
    for cdef in classdefs[1:]:
        result = result.commonbase(cdef)
        if result is None:
            raise TyperError("no common base class in %r" % (classdefs,))
    return result

def allattributenames(classdef):
    for cdef1 in classdef.getmro():
        for attrname in cdef1.attrs:
            yield cdef1, attrname
