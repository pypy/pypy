import types
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.rpython.lltype import typeOf, Void
from pypy.rpython.rmodel import Repr, TyperError
from pypy.rpython import rclass


class __extend__(annmodel.SomePBC):
    def rtyper_makerepr(self, rtyper):
        # for now, we require that the PBC fits neatly into one of the Repr
        # categories below, and doesn't for example mix functions, classes
        # and methods.
        callb = rtyper.annotator.getpbccallables()
        choices = {}
        for x, classdef in self.prebuiltinstances.items():
            cdefflag = isclassdef(classdef)

            # consider unbound methods as plain functions
            if isinstance(x, types.MethodType) and x.im_self is None:
                x = x.im_func

            # callable or frozen object?
            if x in callb:
                # what type of callable?
                if isinstance(x, types.FunctionType):
                    if cdefflag:
                        choice = MethodsPBCRepr
                        cdefflag = False
                    else:
                        choice = FunctionsPBCRepr
                elif isinstance(x, (type, types.ClassType)):
                    choice = ClassesPBCRepr
                #elif isinstance(x, types.MethodType):
                #    choice = ConstMethodsPBCRepr
                else:
                    raise TyperError("don't know about callable %r" % (x,))
            else:
                # frozen object
                choice = FrozenPBCRepr

            if cdefflag:
                raise TyperError("unexpected classdef in PBC set %r" % (
                    self.prebuiltinstances,))
            choices[choice] = True

        if len(choices) > 1:
            raise TyperError("mixed kinds of PBC in the set %r" % (
                self.prebuiltinstances,))
        reprcls, = choices
        return reprcls(rtyper, self)

    def rtyper_makekey(self):
        lst = self.prebuiltinstances.items()
        lst.sort()
        return tuple(lst)


# ____________________________________________________________


class FrozenPBCRepr(Repr):
    """Representation selected for a single non-callable pre-built constant."""
    lowleveltype = Void

    def __init__(self, rtyper, s_pbc):
        assert len(s_pbc.prebuiltinstances) == 1   # XXX not implemented

    def rtype_getattr(_, hop):
        if not hop.s_result.is_constant():
            raise TyperError("getattr on a constant PBC returns a non-constant")
        return hop.inputconst(hop.r_result, hop.s_result.const)


# ____________________________________________________________


def getsignature(rtyper, func):
    f = rtyper.getfunctionptr(func)
    graph = f._obj.graph
    FUNCPTR = typeOf(f)
    rinputs = [rtyper.bindingrepr(v) for v in graph.getargs()]
    if graph.getreturnvar() in rtyper.annotator.bindings:
        rresult = rtyper.bindingrepr(graph.getreturnvar())
    else:
        rresult = Void
    return f, rinputs, rresult


class FunctionsPBCRepr(Repr):
    """Representation selected for a PBC of function(s)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        self.function_signatures = {}
        for func in s_pbc.prebuiltinstances:
            self.function_signatures[func] = getsignature(rtyper, func)

        if len(self.function_signatures) == 1:
            # a single function
            self.lowleveltype = Void
        else:
            signatures = self.function_signatures.values()
            sig0 = signatures[0]
            for sig1 in signatures[1:]:
                assert typeOf(sig0[0]) == typeOf(sig1[0])  # XXX not implemented
                assert sig0[1:] == sig1[1:]                # XXX not implemented
            self.lowleveltype = typeOf(sig0[0])

##            callfamilies = rtyper.annotator.getpbccallfamilies()
##            try:
##                _, _, callfamily = callfamilies[None, functions[0]]
##            except KeyError:
##                self.lowleveltype = Void   # no call family found
##            else:
##                shapes = callfamily.patterns
##                assert len(shapes) == 1, "XXX not implemented"
##                shape, = shapes
##                shape_cnt, shape_keys, shape_star, shape_stst = shape
##                assert not shape_keys, "XXX not implemented"
##                assert not shape_star, "XXX not implemented"
##                assert not shape_stst, "XXX not implemented"

    def convert_const(self, value):
        if value not in self.function_signatures:
            raise TyperError("%r not in %r" % (value,
                                               self.s_pbc.prebuiltinstances))
        f, rinputs, rresult = self.function_signatures[value]
        return f

    def rtype_simple_call(self, hop):
        f, rinputs, rresult = self.function_signatures.itervalues().next()
        vlist = hop.inputargs(self, *rinputs)
        if self.lowleveltype == Void:
            assert len(self.function_signatures) == 1
            vlist[0] = hop.inputconst(typeOf(f), f)
        return hop.genop('direct_call', vlist, resulttype = rresult)


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


class MethodsPBCRepr(Repr):
    """Representation selected for a PBC of the form {func: classdef...}.
    It assumes that all the methods come from the same name in a base
    classdef."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
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
        self.r_instance = rclass.getinstancerepr(rtyper, self.classdef)
        self.lowleveltype = self.r_instance.lowleveltype

    def rtype_simple_call(self, hop):
        # XXX the graph of functions used as methods may need to be hacked
        # XXX so that its 'self' argument accepts a pointer to an instance of
        # XXX the common base class.  This is needed to make the direct_call
        # XXX below well-typed.
        r_class = self.r_instance.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        assert isinstance(r_func, FunctionsPBCRepr)
        #
        # XXX try to unify with FunctionsPBCRepr.rtype_simple_call()
        f, rinputs, rresult = r_func.function_signatures.itervalues().next()
        vlist = hop.inputargs(self, *rinputs[1:])  # ignore the self from r_func
        if r_func.lowleveltype == Void:
            assert len(r_func.function_signatures) == 1
            vfunc = hop.inputconst(typeOf(f), f)
        else:
            vinst = vlist[0]
            vcls = self.r_instance.getfield(vinst, '__class__', hop.llops)
            vfunc = r_class.getclsfield(vcls, self.methodname, hop.llops)
        vlist.insert(0, vfunc)
        return hop.genop('direct_call', vlist, resulttype = rresult)


# ____________________________________________________________


class ClassesPBCRepr(Repr):
    """Representation selected for a PBC of class(es)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        assert s_pbc.is_constant()      # XXX not implemented
        self.lowleveltype = Void
##        self.classdefs = {}
##        for cls in s_pbc.prebuiltinstances:
##            self.classdefs[cls] = rtyper.annotator.getuserclasses()[cls]
##        classdefslist = self.classdefs.values()
##        commonbase = classdefslist[0]
##        for cdef in classdefslist[1:]:
##            commonbase = cdef.commonbase(commonbase)
##            if commonbase is None:
##                raise TyperError("no common base class in PBC set %r" % (
##                    s_pbc.prebuiltinstances,))

    def rtype_simple_call(self, hop):
        return rclass.rtype_new_instance(self.s_pbc.const, hop)
        # XXX call __init__ somewhere
