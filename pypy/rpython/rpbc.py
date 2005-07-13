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
                choice = MethodsPBCRepr

            elif x is None:
                continue    # skipped, a None is allowed implicitely anywhere

            elif isinstance(x, (type, types.ClassType)):
                # classes
                if x in userclasses:
                    # user classes
                    choice = ClassesPBCRepr
                elif type(x) is type and x.__module__ == '__builtin__':
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
                    choice = MethodOfFrozenPBCRepr
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
        return tuple(lst)

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


def getFrozenPBCRepr(rtyper, s_pbc):
    if len(s_pbc.prebuiltinstances) <= 1:
        #if s_pbc.const is None:   -- take care of by rtyper_makerepr() above
        #    return none_frozen_pbc_repr
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
            rtyper.reprs_must_call_setup.append(result)
            return result


class SingleFrozenPBCRepr(Repr):
    """Representation selected for a single non-callable pre-built constant."""
    lowleveltype = Void

    def rtype_getattr(_, hop):
        if not hop.s_result.is_constant():
            raise TyperError("getattr on a constant PBC returns a non-constant")
        return hop.inputconst(hop.r_result, hop.s_result.const)

single_frozen_pbc_repr = SingleFrozenPBCRepr()

# __ None ____________________________________________________
class NoneFrozenPBCRepr(SingleFrozenPBCRepr):
    
    def rtype_is_true(self, hop):
        return Constant(False, Bool)

none_frozen_pbc_repr = NoneFrozenPBCRepr()


def rtype_is_None(robj1, rnone2, hop, pos=0):
        if not isinstance(robj1.lowleveltype, Ptr):
            raise TyperError('is None of instance of the non-pointer: %r' % (robj1))           
        v1 = hop.inputarg(robj1, pos)
        return hop.genop('ptr_iszero', [v1], resulttype=Bool)
    
class __extend__(pairtype(Repr, NoneFrozenPBCRepr)):
    
    def rtype_is_((robj1, rnone2), hop):
        return rtype_is_None(robj1, rnone2, hop)

class __extend__(pairtype(NoneFrozenPBCRepr, Repr)):

    def convert_from_to((_, r_to), v, llops):
        return inputconst(r_to, None)

    def rtype_is_((rnone1, robj2), hop):
        return rtype_is_None(robj2, rnone1, hop, pos=1)
        
class __extend__(pairtype(NoneFrozenPBCRepr, robject.PyObjRepr)):

    def convert_from_to(_, v, llops):
        return inputconst(robject.pyobj_repr, None)

# ____________________________________________________________

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
        if isinstance(pbc, types.MethodType) and pbc.im_self is None:
            value = pbc.im_func   # unbound method -> bare function
##        if pbc not in self.access_set.objects:
##            raise TyperError("not found in PBC set: %r" % (pbc,))
        try:
            return self.pbc_cache[pbc]
        except KeyError:
            self.setup()
            result = malloc(self.pbc_type, immortal=True)
            self.pbc_cache[pbc] = result
            for attr, (mangled_name, r_value) in self.llfieldmap.items():
                try: 
                    thisattrvalue = self.access_set.values[(pbc, attr)] 
                except KeyError:
                    try:
                        thisattrvalue = getattr(pbc, attr)
                    except AttributeError:
                        warning("PBC %r has no attribute %r" % (pbc, attr))
                        continue
                llvalue = r_value.convert_const(thisattrvalue)
                setattr(result, mangled_name, llvalue)
            return result

    def rtype_is_true(self, hop):
        if hop.s_result.is_constant():
            assert hop.s_result.const is True    # custom __nonzero__ on PBCs?
            return hop.inputconst(Bool, hop.s_result.const)
        else:
            # None is a nullptr, which is false; everything else is true.
            vlist = hop.inputargs(self)
            return hop.genop('ptr_nonzero', vlist, resulttype=Bool)

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        vpbc, vattr = hop.inputargs(self, Void)
        return self.getfield(vpbc, attr, hop.llops)

    def getfield(self, vpbc, attr, llops):
        mangled_name, r_value = self.llfieldmap[attr]
        cmangledname = inputconst(Void, mangled_name)
        return llops.genop('getfield', [vpbc, cmangledname],
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
        if isinstance(hop2.args_v[0], Constant):
            hop2.args_v[0] = hop.inputarg(self, 0)
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
        extravlist = []
        if getattr(f._obj.graph, 'normalized_for_calls', False):
            # should not have an argument count mismatch
            assert len(rinputs) == hop.nb_args-1, "normalization bug"
        else:
            # if not normalized, should be a call to a known function
            assert len(self.function_signatures()) == 1, "normalization bug"
            func, = self.function_signatures().keys()
            if has_varargs(func):
                # collect the arguments for '*arg' into a tuple
                rstar = rinputs[-1]
                rinputs = rinputs[:-1]
                assert isinstance(rstar, rtuple.TupleRepr)
                tupleitems_v = []
                for i in range(1+len(rinputs), hop.nb_args):
                    v = hop.inputarg(rstar.items_r[len(tupleitems_v)], arg=i)
                    tupleitems_v.append(v)
                vtuple = rtuple.newtuple(hop.llops, rstar, tupleitems_v)
                extravlist.append(vtuple)
                hop = hop.copy()
                del hop.args_v[1+len(rinputs):]
                del hop.args_s[1+len(rinputs):]
                del hop.args_r[1+len(rinputs):]
                hop.nb_args = len(hop.args_v)

            defaults = func.func_defaults or ()
            if len(rinputs) - len(defaults) <= hop.nb_args-1 <= len(rinputs):
                rinputs = list(rinputs)
                defaults = list(defaults)
                while len(rinputs) > hop.nb_args-1:
                    c = hop.inputconst(rinputs.pop(), defaults.pop())
                    extravlist.insert(0, c)
            else:
                if hop.nb_args-1 > len(rinputs):
                    raise TyperError("too many arguments in function call")
                else:
                    raise TyperError("not enough arguments in function call")
        vlist = hop.inputargs(self, *rinputs) + extravlist
        if self.lowleveltype == Void:
            assert len(self.function_signatures()) == 1
            vlist[0] = hop.inputconst(typeOf(f), f)
        v = hop.genop('direct_call', vlist, resulttype = rresult)
        return hop.llops.convertvar(v, rresult, hop.r_result)

    def rtype_call_args(self, hop):
        f, rinputs, rresult = self.function_signatures().itervalues().next()
        # the function arguments may have been normalized by normalizecalls()
        # already
        if not getattr(f._obj.graph, 'normalized_for_calls', False):
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
        self.s_im_self = annmodel.SomeInstance(self.classdef)
        self.r_im_self = rclass.getinstancerepr(rtyper, self.classdef)
        self.lowleveltype = self.r_im_self.lowleveltype

    def convert_const(self, method):
        if getattr(method, 'im_func', None) is None:
            raise TyperError("not a bound method: %r" % method)
        return self.r_im_self.convert_const(method.im_self)

    def get_method_from_instance(self, r_inst, v_inst, llops):
        # The 'self' might have to be cast to a parent class
        # (as shown for example in test_rclass/test_method_both_A_and_B)
        return llops.convertvar(v_inst, r_inst, self.r_im_self)

    def rtype_simple_call(self, hop):
        r_class = self.r_im_self.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        assert isinstance(r_func, FunctionsPBCRepr)
        s_func = r_func.s_pbc

        hop2 = hop.copy()
        hop2.args_s[0] = self.s_im_self   # make the 1st arg stand for 'im_self'
        hop2.args_r[0] = self.r_im_self   # (same lowleveltype as 'self')

        v_im_self = hop.inputarg(self, arg=0)
        v_cls = self.r_im_self.getfield(v_im_self, '__class__', hop.llops)
        v_func = r_class.getclsfield(v_cls, self.methodname, hop.llops)
        hop2.v_s_insertfirstarg(v_func, s_func)   # insert 'function'
        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch()


# ____________________________________________________________


class ClassesPBCRepr(Repr):
    """Representation selected for a PBC of class(es)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        assert None not in s_pbc.prebuiltinstances, "XXX not implemented"
        if s_pbc.is_constant():
            self.lowleveltype = Void
        else:
            self.lowleveltype = rclass.TYPEPTR
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
        if self.lowleveltype == Void:
            return cls
        return rclass.get_type_repr(self.rtyper).convert_const(cls)

    def rtype_simple_call(self, hop):
        if self.lowleveltype != Void:
            # instantiating a class from multiple possible classes
            vcls = hop.inputarg(self, arg=0)
            access_set = self.get_access_set()
            vnewfn = self.get_class_repr().getpbcfield(vcls, access_set,
                                                       '__new__', hop.llops)
            hop2 = hop.copy()
            hop2.r_s_popfirstarg()   # discard the class pointer argument
            hop2.v_s_insertfirstarg(vnewfn, access_set.attrs['__new__'])
            # now hop2 looks like simple_call(klass__new__, args...)
            return hop2.dispatch()

        # instantiating a single class
        klass = self.s_pbc.const
        v_instance = rclass.rtype_new_instance(hop.rtyper, klass, hop.llops)
        try:
            initfunc = klass.__init__.im_func
        except AttributeError:
            assert hop.nb_args == 1, ("arguments passed to __init__, "
                                      "but no __init__!")
        else:
            s_instance = rclass.instance_annotation_for_cls(self.rtyper, klass)
            s_init = self.rtyper.annotator.bookkeeper.immutablevalue(initfunc)
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

class __extend__(pairtype(ClassesPBCRepr, rclass.ClassRepr)):
    def convert_from_to((r_clspbc, r_cls), v, llops):
        if r_cls.lowleveltype != r_clspbc.lowleveltype:
            return NotImplemented   # good enough for now
        return v

# ____________________________________________________________

def rtype_call_memo(hop): 
    memo_table = hop.args_v[0].value
    if memo_table.s_result.is_constant():
        return hop.inputconst(hop.r_result, memo_table.s_result.const)
    fieldname = memo_table.fieldname 
    assert hop.nb_args == 2, "XXX"  

    r_pbc = hop.args_r[1]
    assert isinstance(r_pbc, (MultipleFrozenPBCRepr, ClassesPBCRepr))
    v_table, v_pbc = hop.inputargs(Void, r_pbc)
    return r_pbc.getfield(v_pbc, fieldname, hop.llops)
