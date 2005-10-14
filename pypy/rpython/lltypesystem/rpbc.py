import types
import sys
from pypy.annotation.pairtype import pairtype, pair
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import typeOf, Void, ForwardReference, Struct, Bool
from pypy.rpython.lltype import Ptr, malloc, nullptr
from pypy.rpython.rmodel import Repr, TyperError, inputconst, warning
from pypy.rpython import robject
from pypy.rpython import rtuple
from pypy.rpython.rpbc import SingleFrozenPBCRepr, getsignature, samesig,\
                                commonbase, allattributenames, get_access_set,\
                                MultiplePBCRepr, FunctionsPBCRepr
from pypy.rpython.lltypesystem import rclass
from pypy.tool.sourcetools import has_varargs

from pypy.rpython import callparse

def rtype_is_None(robj1, rnone2, hop, pos=0):
    if not isinstance(robj1.lowleveltype, Ptr):
        raise TyperError('is None of instance of the non-pointer: %r' % (robj1))           
    v1 = hop.inputarg(robj1, pos)
    return hop.genop('ptr_iszero', [v1], resulttype=Bool)
    
# ____________________________________________________________

class MultipleFrozenPBCRepr(MultiplePBCRepr):
    """Representation selected for multiple non-callable pre-built constants."""
    def __init__(self, rtyper, access_set):
        self.rtyper = rtyper
        self.access_set = access_set
        self.pbc_type = ForwardReference()
        self.lowleveltype = Ptr(self.pbc_type)
        self.pbc_cache = {}

    def _setup_repr(self):
        llfields = []
        llfieldmap = {}
        if self.access_set is not None:
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
                if r_value.lowleveltype is Void:
                    continue
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

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        vpbc, vattr = hop.inputargs(self, Void)
        return self.getfield(vpbc, attr, hop.llops)

    def getfield(self, vpbc, attr, llops):
        mangled_name, r_value = self.llfieldmap[attr]
        cmangledname = inputconst(Void, mangled_name)
        return llops.genop('getfield', [vpbc, cmangledname],
                           resulttype = r_value)

class __extend__(pairtype(MultipleFrozenPBCRepr, MultipleFrozenPBCRepr)):
    def convert_from_to((r_pbc1, r_pbc2), v, llops):
        if r_pbc1.access_set == r_pbc2.access_set:
            return v
        return NotImplemented

class __extend__(pairtype(SingleFrozenPBCRepr, MultipleFrozenPBCRepr)):
    def convert_from_to((r_pbc1, r_pbc2), v, llops):
        value = r_pbc1.value
        access = get_access_set(r_pbc2.rtyper, value)
        if access is r_pbc2.access_set:
            return inputconst(r_pbc2, value)
        return NotImplemented

# ____________________________________________________________


class MethodOfFrozenPBCRepr(Repr):
    """Representation selected for a PBC of method object(s) of frozen PBCs.
    It assumes that all methods are the same function bound to different PBCs.
    The low-level representation can then be a pointer to that PBC."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.function = s_pbc.prebuiltinstances.keys()[0].im_func
        # a hack to force the underlying function to show up in call_families
        # (generally not needed, as normalizecalls() should ensure this,
        # but needed for bound methods that are ll helpers)
        call_families = rtyper.annotator.getpbccallfamilies()
        call_families.find((None, self.function))
        im_selves = {}
        for pbc, not_a_classdef in s_pbc.prebuiltinstances.items():
            if pbc is None:
                raise TyperError("unsupported: variable of type "
                                 "method-of-frozen-PBC or None")
            assert pbc.im_func is self.function
            assert not isclassdef(not_a_classdef)
            im_selves[pbc.im_self] = True
        self.s_im_self = annmodel.SomePBC(im_selves)
        self.r_im_self = rtyper.getrepr(self.s_im_self)
        self.lowleveltype = self.r_im_self.lowleveltype

    def get_s_callable(self):
        return annmodel.SomePBC({self.function: True})

    def get_r_implfunc(self):
        r_func = self.rtyper.getrepr(self.get_s_callable())
        return r_func, 1

    def convert_const(self, method):
        if getattr(method, 'im_func', None) is not self.function:
            raise TyperError("not a method bound on %r: %r" % (self.function,
                                                               method))
        return self.r_im_self.convert_const(method.im_self)

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        s_function = annmodel.SomePBC({self.function: True})
        hop2 = hop.copy()
        hop2.args_s[0] = self.s_im_self   # make the 1st arg stand for 'im_self'
        hop2.args_r[0] = self.r_im_self   # (same lowleveltype as 'self')
        if isinstance(hop2.args_v[0], Constant):
            hop2.args_v[0] = hop.inputarg(self, 0)
        if call_args:
            hop2.swap_fst_snd_args()
            _, s_shape = hop2.r_s_popfirstarg() # temporarely remove shape
            adjust_shape(hop2, s_shape)
        c = Constant(self.function)
        hop2.v_s_insertfirstarg(c, s_function)   # insert 'function'
        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch()

def adjust_shape(hop2, s_shape):
    new_shape = (s_shape.const[0]+1,) + s_shape.const[1:]
    c_shape = Constant(new_shape)
    s_shape = hop2.rtyper.annotator.bookkeeper.immutablevalue(new_shape)
    hop2.v_s_insertfirstarg(c_shape, s_shape) # reinsert adjusted shape
    
# ____________________________________________________________

class MethodsPBCRepr(Repr):
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

    def rtype_hardwired_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False, hardwired=True)

    def rtype_hardwired_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True, hardwired=True)

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args, hardwired=False):
        hop2 = hop.copy()
        if hardwired:
            hop2.swap_fst_snd_args() # bring the hardwired function constant in front
            func = hop2.args_v[0].value
            s_func = annmodel.SomePBC({func: True})
            hop2.r_s_popfirstarg() # info captured, discard it
            v_func = Constant(func)
        else:
            r_class = self.r_im_self.rclass
            mangled_name, r_func = r_class.clsfields[self.methodname]
            assert isinstance(r_func, FunctionsPBCRepr)
            s_func = r_func.s_pbc
            v_im_self = hop.inputarg(self, arg=0)
            v_cls = self.r_im_self.getfield(v_im_self, '__class__', hop.llops)
            v_func = r_class.getclsfield(v_cls, self.methodname, hop.llops)

        hop2.args_s[0] = self.s_im_self   # make the 1st arg stand for 'im_self'
        hop2.args_r[0] = self.r_im_self   # (same lowleveltype as 'self')

        opname = 'simple_call'
        if call_args:
            hop2.swap_fst_snd_args()
            _, s_shape = hop2.r_s_popfirstarg()
            adjust_shape(hop2, s_shape)
            opname = 'call_args'

        hop2.v_s_insertfirstarg(v_func, s_func)   # insert 'function'
        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch(opname=opname)


# ____________________________________________________________


class ClassesPBCRepr(Repr):
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
        if self.lowleveltype is Void:
            return cls
        return rclass.get_type_repr(self.rtyper).convert_const(cls)

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        if self.lowleveltype is not Void:
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
            if call_args:
                _, s_shape = hop2.r_s_popfirstarg() # temporarely remove shape
                hop2.v_s_insertfirstarg(v_instance, s_instance)  # add 'instance'
                adjust_shape(hop2, s_shape)
            else:
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

class __extend__(pairtype(ClassesPBCRepr, rclass.AbstractClassRepr)):
    def convert_from_to((r_clspbc, r_cls), v, llops):
        if r_cls.lowleveltype != r_clspbc.lowleveltype:
            return NotImplemented   # good enough for now
        return v

class __extend__(pairtype(ClassesPBCRepr, ClassesPBCRepr)):
        def convert_from_to((r_clspbc1, r_clspbc2), v, llops):
            # this check makes sense because both source and dest repr are ClassesPBCRepr
            if r_clspbc1.lowleveltype == r_clspbc2.lowleveltype:
                return v
            if r_clspbc1.lowleveltype is Void:
                return inputconst(r_clspbc2, r_clspbc1.s_pbc.const)
            return NotImplemented
            


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
