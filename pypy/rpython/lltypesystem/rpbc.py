import types
import sys
from pypy.annotation.pairtype import pairtype, pair
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Void, ForwardReference, Struct, Bool, \
     Ptr, malloc, nullptr
from pypy.rpython.rmodel import Repr, TyperError, inputconst, inputdesc
from pypy.rpython.rpbc import samesig,\
     commonbase, allattributenames, adjust_shape, \
     AbstractClassesPBCRepr, AbstractMethodsPBCRepr, OverriddenFunctionPBCRepr, \
     AbstractMultipleFrozenPBCRepr, MethodOfFrozenPBCRepr, \
     AbstractFunctionsPBCRepr, AbstractMultipleUnrelatedFrozenPBCRepr, \
     SingleFrozenPBCRepr
from pypy.rpython.lltypesystem import rclass, llmemory
from pypy.tool.sourcetools import has_varargs

from pypy.rpython import callparse

def rtype_is_None(robj1, rnone2, hop, pos=0):
    if isinstance(robj1.lowleveltype, Ptr):
        v1 = hop.inputarg(robj1, pos)
        return hop.genop('ptr_iszero', [v1], resulttype=Bool)
    elif robj1.lowleveltype == llmemory.Address:
        v1 = hop.inputarg(robj1, pos)
        cnull = hop.inputconst(llmemory.Address, robj1.null_instance())
        return hop.genop('adr_eq', [v1, cnull], resulttype=Bool)
    else:
        raise TyperError('rtype_is_None of %r' % (robj1))

# ____________________________________________________________

class MultipleFrozenPBCRepr(AbstractMultipleFrozenPBCRepr):
    """Representation selected for multiple non-callable pre-built constants."""
    def __init__(self, rtyper, access_set):
        self.rtyper = rtyper
        self.access_set = access_set
        self.pbc_type = ForwardReference()
        self.lowleveltype = Ptr(self.pbc_type)
        self.pbc_cache = {}

    def _setup_repr(self):
        llfields = self._setup_repr_fields()
        self.pbc_type.become(Struct('pbc', *llfields))

    def create_instance(self):
        return malloc(self.pbc_type, immortal=True)

    def null_instance(self):
        return nullptr(self.pbc_type)

    def getfield(self, vpbc, attr, llops):
        mangled_name, r_value = self.fieldmap[attr]
        cmangledname = inputconst(Void, mangled_name)
        return llops.genop('getfield', [vpbc, cmangledname],
                           resulttype = r_value)


class MultipleUnrelatedFrozenPBCRepr(AbstractMultipleUnrelatedFrozenPBCRepr):
    """Representation selected for multiple non-callable pre-built constants
    with no common access set."""

    lowleveltype = llmemory.Address
    EMPTY = Struct('pbc')

    def convert_pbc(self, pbcptr):
        return llmemory.fakeaddress(pbcptr)

    def create_instance(self):
        return malloc(self.EMPTY, immortal=True)

    def null_instance(self):
        return llmemory.Address._defl()

class __extend__(pairtype(MultipleUnrelatedFrozenPBCRepr,
                          MultipleUnrelatedFrozenPBCRepr),
                 pairtype(MultipleUnrelatedFrozenPBCRepr,
                          SingleFrozenPBCRepr),
                 pairtype(SingleFrozenPBCRepr,
                          MultipleUnrelatedFrozenPBCRepr)):
    def rtype_is_((robj1, robj2), hop):
        if isinstance(robj1, MultipleUnrelatedFrozenPBCRepr):
            r = robj1
        else:
            r = robj2
        vlist = hop.inputargs(r, r)
        return hop.genop('adr_eq', vlist, resulttype=Bool)

class __extend__(pairtype(MultipleFrozenPBCRepr,
                          MultipleUnrelatedFrozenPBCRepr)):
    def convert_from_to((robj1, robj2), v, llops):
        return llops.genop('cast_ptr_to_adr', [v], resulttype=llmemory.Address)

# ____________________________________________________________

class FunctionsPBCRepr(AbstractFunctionsPBCRepr):
    """Representation selected for a PBC of function(s)."""

    def setup_specfunc(self):
        fields = []
        for row in self.uniquerows:
            fields.append((row.attrname, row.fntype))
        return Ptr(Struct('specfunc', *fields))
        
    def create_specfunc(self):
        return malloc(self.lowleveltype.TO, immortal=True)

    def get_specfunc_row(self, llop, v, c_rowname, resulttype):
        return llop.genop('getfield', [v, c_rowname], resulttype=resulttype)
        
class MethodsPBCRepr(AbstractMethodsPBCRepr):
    """Representation selected for a PBC of the form {func: classdef...}.
    It assumes that all the methods come from the same name in a base
    classdef."""

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        r_class = self.r_im_self.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        assert isinstance(r_func, (FunctionsPBCRepr,
                                   OverriddenFunctionPBCRepr))
        # s_func = r_func.s_pbc -- not precise enough, see
        # test_precise_method_call_1.  Build a more precise one...
        funcdescs = [desc.funcdesc for desc in hop.args_s[0].descriptions]
        s_func = annmodel.SomePBC(funcdescs)
        v_im_self = hop.inputarg(self, arg=0)
        v_cls = self.r_im_self.getfield(v_im_self, '__class__', hop.llops)
        v_func = r_class.getclsfield(v_cls, self.methodname, hop.llops)

        hop2 = self.add_instance_arg_to_hop(hop, call_args)
        opname = 'simple_call'
        if call_args:
            opname = 'call_args'

        hop2.v_s_insertfirstarg(v_func, s_func)   # insert 'function'
        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch(opname=opname)


# ____________________________________________________________


class ClassesPBCRepr(AbstractClassesPBCRepr):
    """Representation selected for a PBC of class(es)."""

    # no __init__ here, AbstractClassesPBCRepr.__init__ is good enough

    def _instantiate_runtime_class(self, hop, vtypeptr, r_instance):
        from pypy.rpython.lltypesystem.rbuiltin import ll_instantiate
        v_inst1 = hop.gendirectcall(ll_instantiate, vtypeptr)
        return hop.genop('cast_pointer', [v_inst1], resulttype = r_instance)



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
