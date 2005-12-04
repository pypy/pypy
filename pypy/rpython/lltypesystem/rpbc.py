import types
import sys
from pypy.annotation.pairtype import pairtype, pair
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Void, ForwardReference, Struct, Bool, \
     Ptr, malloc, nullptr
from pypy.rpython.rmodel import Repr, TyperError, inputconst, inputdesc
from pypy.rpython.rmodel import warning, mangle, CanBeNull
from pypy.rpython import robject
from pypy.rpython import rtuple
from pypy.rpython.rpbc import SingleFrozenPBCRepr, samesig,\
     commonbase, allattributenames, FunctionsPBCRepr, \
     AbstractClassesPBCRepr, AbstractMethodsPBCRepr, OverriddenFunctionPBCRepr
from pypy.rpython.lltypesystem import rclass
from pypy.tool.sourcetools import has_varargs

from pypy.rpython import callparse

def rtype_is_None(robj1, rnone2, hop, pos=0):
    if not isinstance(robj1.lowleveltype, Ptr):
        raise TyperError('is None of instance of the non-pointer: %r' % (robj1))           
    v1 = hop.inputarg(robj1, pos)
    return hop.genop('ptr_iszero', [v1], resulttype=Bool)
    
# ____________________________________________________________

class MultipleFrozenPBCRepr(CanBeNull, Repr):
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
                mangled_name = mangle('pbc', attr)
                llfields.append((mangled_name, r_value.lowleveltype))
                llfieldmap[attr] = mangled_name, r_value
        self.pbc_type.become(Struct('pbc', *llfields))
        self.llfieldmap = llfieldmap

    def convert_desc(self, frozendesc):
        if (self.access_set is not None and
            frozendesc not in self.access_set.descs):
            raise TyperError("not found in PBC access set: %r" % (frozendesc,))
        try:
            return self.pbc_cache[frozendesc]
        except KeyError:
            self.setup()
            result = malloc(self.pbc_type, immortal=True)
            self.pbc_cache[frozendesc] = result
            for attr, (mangled_name, r_value) in self.llfieldmap.items():
                if r_value.lowleveltype is Void:
                    continue
                try:
                    thisattrvalue = frozendesc.read_attribute(attr)
                except AttributeError:
                    warning("Desc %r has no attribute %r" % (frozendesc, attr))
                    continue
                llvalue = r_value.convert_const(thisattrvalue)
                setattr(result, mangled_name, llvalue)
            return result

    def convert_const(self, pbc):
        if pbc is None:
            return nullptr(self.pbc_type)
        if isinstance(pbc, types.MethodType) and pbc.im_self is None:
            value = pbc.im_func   # unbound method -> bare function
        frozendesc = self.rtyper.annotator.bookkeeper.getdesc(pbc)
        return self.convert_desc(frozendesc)

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        vpbc, vattr = hop.inputargs(self, Void)
        v_res = self.getfield(vpbc, attr, hop.llops)
        mangled_name, r_res = self.llfieldmap[attr]
        return hop.llops.convertvar(v_res, r_res, hop.r_result)

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
        frozendesc1 = r_pbc1.frozendesc
        access = frozendesc1.queryattrfamily()
        if access is r_pbc2.access_set:
            return inputdesc(r_pbc2, frozendesc1)
        return NotImplemented

# ____________________________________________________________


class MethodOfFrozenPBCRepr(Repr):
    """Representation selected for a PBC of method object(s) of frozen PBCs.
    It assumes that all methods are the same function bound to different PBCs.
    The low-level representation can then be a pointer to that PBC."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.funcdesc = s_pbc.descriptions.keys()[0].funcdesc

        # a hack to force the underlying function to show up in call_families
        # (generally not needed, as normalizecalls() should ensure this,
        # but needed for bound methods that are ll helpers)
        # XXX sort this out
        #call_families = rtyper.annotator.getpbccallfamilies()
        #call_families.find((None, self.function))
        
        if s_pbc.can_be_none():
            raise TyperError("unsupported: variable of type "
                             "method-of-frozen-PBC or None")

        im_selves = []
        for desc in s_pbc.descriptions:
            assert desc.funcdesc is self.funcdesc
            im_selves.append(desc.frozendesc)
            
        self.s_im_self = annmodel.SomePBC(im_selves)
        self.r_im_self = rtyper.getrepr(self.s_im_self)
        self.lowleveltype = self.r_im_self.lowleveltype

    def get_s_callable(self):
        return annmodel.SomePBC([self.funcdesc])

    def get_r_implfunc(self):
        r_func = self.rtyper.getrepr(self.get_s_callable())
        return r_func, 1

    def convert_desc(self, mdesc):
        if mdesc.funcdesc is not self.funcdesc:
            raise TyperError("not a method bound on %r: %r" % (self.funcdesc, 
                                                               mdesc))
        return self.r_im_self.convert_desc(mdesc.frozendesc)

    def convert_const(self, method):
        mdesc = self.rtyper.annotator.bookkeeper.getdesc(method)
        return self.convert_desc(mdesc)

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        # XXX obscure, try to refactor...
        s_function = annmodel.SomePBC([self.funcdesc])
        hop2 = hop.copy()
        hop2.args_s[0] = self.s_im_self   # make the 1st arg stand for 'im_self'
        hop2.args_r[0] = self.r_im_self   # (same lowleveltype as 'self')
        if isinstance(hop2.args_v[0], Constant):
            boundmethod = hop2.args_v[0].value
            hop2.args_v[0] = Constant(boundmethod.im_self)
        if call_args:
            hop2.swap_fst_snd_args()
            _, s_shape = hop2.r_s_popfirstarg() # temporarely remove shape
            adjust_shape(hop2, s_shape)
        # a marker that would crash if actually used...
        c = Constant("obscure-don't-use-me")
        hop2.v_s_insertfirstarg(c, s_function)   # insert 'function'
        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch()

def adjust_shape(hop2, s_shape):
    new_shape = (s_shape.const[0]+1,) + s_shape.const[1:]
    c_shape = Constant(new_shape)
    s_shape = hop2.rtyper.annotator.bookkeeper.immutablevalue(new_shape)
    hop2.v_s_insertfirstarg(c_shape, s_shape) # reinsert adjusted shape
    
# ____________________________________________________________

class MethodsPBCRepr(AbstractMethodsPBCRepr):
    """Representation selected for a PBC of the form {func: classdef...}.
    It assumes that all the methods come from the same name in a base
    classdef."""

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        hop2 = hop.copy()
        r_class = self.r_im_self.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        assert isinstance(r_func, (FunctionsPBCRepr,
                                   OverriddenFunctionPBCRepr))
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


class ClassesPBCRepr(AbstractClassesPBCRepr):
    """Representation selected for a PBC of class(es)."""

    # no __init__ here, AbstractClassesPBCRepr.__init__ is good enough

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        s_instance = hop.s_result
        r_instance = hop.r_result

        if self.lowleveltype is Void:
            # instantiating a single class
            assert isinstance(s_instance, annmodel.SomeInstance)
            classdef = hop.s_result.classdef
            v_instance = rclass.rtype_new_instance(hop.rtyper, classdef,
                                                   hop.llops)
            s_init = classdef.classdesc.s_read_attribute('__init__')
            v_init = Constant("init-func-dummy")   # this value not really used
        else:
            # instantiating a class from multiple possible classes
            from pypy.rpython.lltypesystem.rbuiltin import ll_instantiate
            vtypeptr = hop.inputarg(self, arg=0)
            access_set = self.get_access_set()
            r_class = self.get_class_repr()
            if '__init__' in access_set.attrs:
                s_init = access_set.attrs['__init__']
                v_init = r_class.getpbcfield(vtypeptr, access_set, '__init__',
                                             hop.llops)
            else:
                s_init = annmodel.s_ImpossibleValue
            v_inst1 = hop.gendirectcall(ll_instantiate, vtypeptr)
            v_instance = hop.genop('cast_pointer', [v_inst1],
                                   resulttype = r_instance)

        if isinstance(s_init, annmodel.SomeImpossibleValue):
            assert hop.nb_args == 1, ("arguments passed to __init__, "
                                      "but no __init__!")
        else:
            hop2 = hop.copy()
            hop2.r_s_popfirstarg()   # discard the class pointer argument
            if call_args:
                _, s_shape = hop2.r_s_popfirstarg() # temporarely remove shape
                hop2.v_s_insertfirstarg(v_instance, s_instance)  # add 'instance'
                adjust_shape(hop2, s_shape)
            else:
                hop2.v_s_insertfirstarg(v_instance, s_instance)  # add 'instance'
            hop2.v_s_insertfirstarg(v_init, s_init)   # add 'initfunc'
            hop2.s_result = annmodel.s_None
            hop2.r_result = self.rtyper.getrepr(hop2.s_result)
            # now hop2 looks like simple_call(initfunc, instance, args...)
            hop2.dispatch()
        return v_instance

# ____________________________________________________________

##def rtype_call_memo(hop): 
##    memo_table = hop.args_v[0].value
##    if memo_table.s_result.is_constant():
##        return hop.inputconst(hop.r_result, memo_table.s_result.const)
##    fieldname = memo_table.fieldname 
##    assert hop.nb_args == 2, "XXX"  

##    r_pbc = hop.args_r[1]
##    assert isinstance(r_pbc, (MultipleFrozenPBCRepr, ClassesPBCRepr))
##    v_table, v_pbc = hop.inputargs(Void, r_pbc)
##    return r_pbc.getfield(v_pbc, fieldname, hop.llops)
