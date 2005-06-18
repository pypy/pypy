import types
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import typeOf, Void, ForwardReference, Struct
from pypy.rpython.lltype import Ptr, malloc, nullptr
from pypy.rpython.rmodel import Repr, TyperError
from pypy.rpython import rclass
from pypy.rpython.rtyper import HighLevelOp


class __extend__(annmodel.SomePBC):
    def rtyper_makerepr(self, rtyper):
        # for now, we require that the PBC fits neatly into one of the Repr
        # categories below, and doesn't for example mix functions, classes
        # and methods.
        call_families = rtyper.annotator.getpbccallfamilies()
        choices = {}
        for x, classdef in self.prebuiltinstances.items():
            cdefflag = isclassdef(classdef)
            if not cdefflag:
                classdef = None

            # consider unbound methods as plain functions
            if isinstance(x, types.MethodType) and x.im_self is None:
                x = x.im_func

            # callable or frozen object?
            if (classdef, x) in call_families:
                # what type of callable?
                if isinstance(x, types.FunctionType):
                    if cdefflag:
                        choice = MethodsPBCRepr
                        cdefflag = False
                    else:
                        choice = FunctionsPBCRepr
                elif isinstance(x, (type, types.ClassType)):
                    choice = ClassesPBCRepr
                elif isinstance(x, types.MethodType):
                    choice = MethodOfFrozenPBCRepr
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


class MethodOfFrozenPBCRepr(Repr):
    """Representation selected for a PBC of method object(s) of frozen PBCs.
    It assumes that all methods are the same function bound to different PBCs.
    The low-level representation can then be a pointer to that PBC."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.function = s_pbc.prebuiltinstances.keys()[0].im_func
        im_selves = {}
        for pbc, not_a_classdef in s_pbc.prebuiltinstances.items():
            assert pbc.im_func is self.function
            assert not isclassdef(not_a_classdef)
            im_selves[pbc.im_self] = True
        self.s_im_self = annmodel.SomePBC(im_selves)
        self.r_im_self = rtyper.getrepr(self.s_im_self)
        self.lowleveltype = self.r_im_self.lowleveltype

    def convert_const(self, method):
        if getattr(method, 'im_func', None) is not self.function:
            raise TyperError("not a method bound on %r: %r" % (self.function,
                                                               method))
        return self.r_im_self.convert_const(method.im_self)

    def rtype_simple_call(self, hop):
        s_function = annmodel.SomePBC({self.function: True})
        hop2 = hop.copy()
        hop2.args_s[0] = self.s_im_self   # make the 1st arg stand for 'im_self'
        hop2.args_r[0] = self.r_im_self   # (same lowleveltype as 'self')
        c = Constant(self.function)
        hop2.v_s_insertfirstarg(c, s_function)   # insert 'function'
        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch()


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
        if isinstance(value, types.MethodType) and value.im_self is None:
            value = value.im_func   # unbound method -> bare function
        if value not in self.function_signatures:
            raise TyperError("%r not in %r" % (value,
                                               self.s_pbc.prebuiltinstances))
        f, rinputs, rresult = self.function_signatures[value]
        return f

    def rtype_simple_call(self, hop):
        f, rinputs, rresult = self.function_signatures.itervalues().next()
        defaultclist = []
        if len(rinputs) != hop.nb_args-1:  # argument count mismatch
            assert not getattr(f._obj.graph, 'normalized_for_calls', False), (
                "normalization bug")
            assert len(self.function_signatures) == 1, "normalization bug too"
            func, = self.function_signatures.keys()
            defaults = func.func_defaults or ()
            if len(rinputs) - len(defaults) <= hop.nb_args-1 <= len(rinputs):
                rinputs = list(rinputs)
                defaults = list(defaults)
                while len(rinputs) != hop.nb_args-1:
                    c = hop.inputconst(rinputs.pop(), defaults.pop())
                    defaultclist.insert(0, c)
            else:
                if hop.nb_args-1 > len(rinputs):
                    raise RTyperError("too many arguments in function call")
                else:
                    raise RTyperError("not enough arguments in function call")
        vlist = hop.inputargs(self, *rinputs) + defaultclist
        if self.lowleveltype == Void:
            assert len(self.function_signatures) == 1
            vlist[0] = hop.inputconst(typeOf(f), f)
        return hop.genop('direct_call', vlist, resulttype = rresult)

    def rtype_call_args(self, hop):
        f, rinputs, rresult = self.function_signatures.itervalues().next()
        # the function arguments may have been normalized by normalizecalls()
        # already
        if not f._obj.graph.normalized_for_calls:
            assert False, "XXX do stuff here"
        vlist = hop.inputargs(self, Void, *rinputs)
        return hop.genop('direct_call', vlist[:1] + vlist[2:],
                         resulttype = rresult)

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
        klass = self.s_pbc.const
        v_instance = rclass.rtype_new_instance(klass, hop)
        try:
            initfunc = klass.__init__.im_func
        except AttributeError:
            assert hop.nb_args == 1, ("arguments passed to __init__, "
                                      "but no __init__!")
        else:
            if initfunc == Exception.__init__.im_func:
                return v_instance    # ignore __init__ and arguments completely
            s_instance = rclass.instance_annotation_for_cls(self.rtyper, klass)
            s_init = annmodel.SomePBC({initfunc: True})
            hop2 = hop.copy()
            hop2.r_s_popfirstarg()   # discard the class pointer argument
            hop2.v_s_insertfirstarg(v_instance, s_instance)  # add 'instance'
            c = Constant(initfunc)
            hop2.v_s_insertfirstarg(c, s_init)   # add 'initfunc'
            hop2.s_result = annmodel.SomePBC({None: True})
            hop2.r_result = self.rtyper.getrepr(hop2.s_result)
            # now hop2 looks like simple_call(initfunc, instance, args...)
            hop2.dispatch()
        return v_instance
