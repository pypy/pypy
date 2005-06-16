import types
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.rpython.lltype import typeOf, Void, ForwardReference, Struct
from pypy.rpython.lltype import Ptr, malloc, nullptr
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
                choice = getFrozenPBCRepr

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


def getFrozenPBCRepr(rtyper, s_pbc):
    if len(s_pbc.prebuiltinstances) <= 1:
        return single_frozen_pbc_repr
    else:
        pbcs = [pbc for pbc in s_pbc.prebuiltinstances.keys()
                    if pbc is not None]
        access_sets = rtyper.annotator.getpbcaccesssets()
        _, _, access = access_sets.find(pbcs[0])
        for obj in pbcs[1:]:
            _, _, access1 = access_sets.find(obj)
            assert access1 is access       # XXX not implemented
        try:
            return rtyper.pbc_reprs[access]
        except KeyError:
            result = MultipleFrozenPBCRepr(rtyper, access)
            rtyper.pbc_reprs[access] = result
            return result


class SingleFrozenPBCRepr(Repr):
    """Representation selected for a single non-callable pre-built constant."""
    lowleveltype = Void

    def rtype_getattr(_, hop):
        if not hop.s_result.is_constant():
            raise TyperError("getattr on a constant PBC returns a non-constant")
        return hop.inputconst(hop.r_result, hop.s_result.const)

single_frozen_pbc_repr = SingleFrozenPBCRepr()


class MultipleFrozenPBCRepr(Repr):
    """Representation selected for multiple non-callable pre-built constants."""
    initialized = False

    def __init__(self, rtyper, access_set):
        self.rtyper = rtyper
        self.access_set = access_set
        self.pbc_type = ForwardReference()
        self.lowleveltype = Ptr(self.pbc_type)
        self.pbc_cache = {}

    def setup(self):
        if self.initialized:
            assert self.initialized == True
            return
        self.initialized = "in progress"
        llfields = []
        llfieldmap = {}
        attrlist = self.access_set.attrs.keys()
        attrlist.sort()
        for attr in attrlist:
            s_value = self.access_set.attrs[attr]
            r_value = self.rtyper.getrepr(s_value)
            mangled_name = 'pbc_' + attr
            llfields.append((mangled_name, r_value.lowleveltype))
            llfieldmap[attr] = mangled_name, r_value
        self.pbc_type.become(Struct('pbc', *llfields))
        self.llfieldmap = llfieldmap
        self.initialized = True

    def convert_const(self, pbc):
        if pbc is None:
            return nullptr(self.pbc_type)
        if pbc not in self.access_set.objects:
            raise TyperError("not found in PBC set: %r" % (pbc,))
        try:
            return self.pbc_cache[pbc]
        except KeyError:
            self.setup()
            result = malloc(self.pbc_type, immortal=True)
            self.pbc_cache[pbc] = result
            for attr, (mangled_name, r_value) in self.llfieldmap.items():
                thisattrvalue = getattr(pbc, attr)
                llvalue = r_value.convert_const(thisattrvalue)
                setattr(result, mangled_name, llvalue)
            return result

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        vpbc, vattr = hop.inputargs(self, Void)
        mangled_name, r_value = self.llfieldmap[attr]
        cmangledname = hop.inputconst(Void, mangled_name)
        return hop.genop('getfield', [vpbc, cmangledname],
                         resulttype = r_value)


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
