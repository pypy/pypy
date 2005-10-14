import types
import sys
from pypy.annotation.pairtype import pairtype, pair
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import typeOf, Void, ForwardReference, Struct, Bool
from pypy.rpython.lltype import Ptr, malloc, nullptr
from pypy.rpython.rmodel import Repr, TyperError, inputconst, warning
from pypy.rpython import rclass
from pypy.rpython import robject
from pypy.rpython import rtuple
from pypy.tool.sourcetools import has_varargs

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
                    choice = rtyper.type_system.rpbc.FunctionsPBCRepr
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
