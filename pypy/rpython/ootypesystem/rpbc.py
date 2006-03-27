from pypy.rpython.rmodel import CanBeNull, Repr, inputconst
from pypy.rpython.rpbc import AbstractClassesPBCRepr, AbstractMethodsPBCRepr, \
        AbstractMultipleFrozenPBCRepr, MethodOfFrozenPBCRepr, \
        AbstractFunctionsPBCRepr, AbstractMultipleUnrelatedFrozenPBCRepr
from pypy.rpython.rclass import rtype_new_instance, getinstancerepr
from pypy.rpython.rpbc import get_concrete_calltable
from pypy.rpython import callparse
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rclass import ClassRepr, InstanceRepr 
from pypy.rpython.ootypesystem.rclass import mangle
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.annotation.pairtype import pairtype
import types


def rtype_is_None(robj1, rnone2, hop, pos=0):
    v1 = hop.inputarg(robj1, pos)
    v2 = hop.genop('oononnull', [v1], resulttype=ootype.Bool)
    v3 = hop.genop('bool_not', [v2], resulttype=ootype.Bool)
    return v3


class FunctionsPBCRepr(AbstractFunctionsPBCRepr):
    """Representation selected for a PBC of function(s)."""

    def setup_specfunc(self):
        fields = {}
        for row in self.uniquerows:
            fields[row.attrname] = row.fntype
        return ootype.Instance('specfunc', ootype.ROOT, fields)

    def create_specfunc(self):
        return ootype.new(self.lowleveltype)

    def get_specfunc_row(self, llop, v, c_rowname, resulttype):
        return llop.genop('oogetfield', [v, c_rowname], resulttype=resulttype)
        
class ClassesPBCRepr(AbstractClassesPBCRepr):

    def rtype_simple_call(self, hop):
        classdef = hop.s_result.classdef
        if self.lowleveltype is not ootype.Void:
            # instantiating a class from multiple possible classes
            v_meta = hop.inputarg(self, arg=0)
            c_class_ = hop.inputconst(ootype.Void, "class_")
            v_class = hop.genop('oogetfield', [v_meta, c_class_],
                    resulttype=ootype.Class)
            resulttype = getinstancerepr(hop.rtyper, classdef).lowleveltype
            v_instance = hop.genop('runtimenew', [v_class], resulttype=resulttype)
            c_meta = hop.inputconst(ootype.Void, "meta")
            hop.genop('oosetfield', [v_instance, c_meta, v_meta],
                    resulttype=ootype.Void)
        else:
            # instantiating a single class
            v_instance = rtype_new_instance(hop.rtyper, classdef, hop.llops)

        inits = []
        for desc in self.s_pbc.descriptions:
            if desc.find_source_for('__init__') is not None:
                unbound = desc.s_get_value(desc.getuniqueclassdef(), '__init__')
                unbound, = unbound.descriptions
                bound = unbound.bind_self(desc.getuniqueclassdef())
                inits.append(bound)

        if inits:
            s_init = annmodel.SomePBC(inits)
            s_instance = annmodel.SomeInstance(classdef)
            hop2 = hop.copy()
            hop2.r_s_popfirstarg()   # discard the class pointer argument
            hop2.v_s_insertfirstarg(v_instance, s_init)  # add 'instance'
            hop2.s_result = annmodel.s_None
            hop2.r_result = self.rtyper.getrepr(hop2.s_result)
            # now hop2 looks like simple_call(initmeth, args...)
            hop2.dispatch()
        else:
            assert hop.nb_args == 1, ("arguments passed to __init__, "
                                      "but no __init__!")
        return v_instance

    rtype_call_args = rtype_simple_call

def row_method_name(methodname, rowname):
    return "%s_%s" % (methodname, rowname)
    
class MethodImplementations(object):

    def __init__(self, rtyper, methdescs):
        samplemdesc = methdescs.iterkeys().next()
        concretetable, uniquerows = get_concrete_calltable(rtyper,
                                             samplemdesc.funcdesc.getcallfamily())
        self.row_mapping = {} 
        for row in uniquerows:
            sample_as_static_meth = row.itervalues().next()
            SM = ootype.typeOf(sample_as_static_meth)
            M = ootype.Meth(SM.ARGS[1:], SM.RESULT) # cut self
            self.row_mapping[row.attrname] = row, M

    def get(rtyper, s_pbc):
        lst = list(s_pbc.descriptions)
        lst.sort()
        key = tuple(lst)
        try:
            return rtyper.oo_meth_impls[key]
        except KeyError:
            methodsimpl = MethodImplementations(rtyper, s_pbc.descriptions)
            rtyper.oo_meth_impls[key] = methodsimpl
            return methodsimpl
    get = staticmethod(get)

    def get_impl(self, name, methdesc, is_finalizer=False):
        impls = {}
        flags = {}
        if is_finalizer:
            flags['finalizer'] = True
        for rowname, (row, M) in self.row_mapping.iteritems():
            if methdesc is None:
                m = ootype.meth(M, _name=name, abstract=True, **flags)
            else:
                impl_graph = row[methdesc.funcdesc].graph
                m = ootype.meth(M, _name=name, graph=impl_graph, **flags)
            derived_name = row_method_name(name, rowname)
            impls[derived_name] = m
        return impls


class MethodsPBCRepr(AbstractMethodsPBCRepr):

    def __init__(self, rtyper, s_pbc):
        AbstractMethodsPBCRepr.__init__(self, rtyper, s_pbc)
        sampledesc = s_pbc.descriptions.iterkeys().next()
        self.concretetable, _ = get_concrete_calltable(rtyper,
                                             sampledesc.funcdesc.getcallfamily())

    def rtype_simple_call(self, hop):
        return self.call("simple_call", hop)

    def rtype_call_args(self, hop):
        return self.call("call_args", hop)

    def call(self, opname, hop):
        bk = self.rtyper.annotator.bookkeeper
        args = bk.build_args(opname, hop.args_s[1:])
        args = args.prepend(self.s_im_self)
        s_pbc = hop.args_s[0]   # possibly more precise than self.s_pbc
        descs = [desc.funcdesc for desc in s_pbc.descriptions]
        callfamily = descs[0].getcallfamily()
        shape, index = description.FunctionDesc.variant_for_call_site(
                bk, callfamily, descs, args)
        row_of_graphs = callfamily.calltables[shape][index]
        anygraph = row_of_graphs.itervalues().next()  # pick any witness
        hop2 = self.add_instance_arg_to_hop(hop, opname == "call_args")
        vlist = callparse.callparse(self.rtyper, anygraph, hop2, opname,
                is_method=True)
        rresult = callparse.getrresult(self.rtyper, anygraph)
        hop.exception_is_here()
        mangled = mangle(self.methodname)
        row = self.concretetable[shape, index]
        derived_mangled = row_method_name(mangled, row.attrname)
        cname = hop.inputconst(ootype.Void, derived_mangled)
        v = hop.genop("oosend", [cname]+vlist, resulttype=rresult)
        return hop.llops.convertvar(v, rresult, hop.r_result)
        

class __extend__(pairtype(InstanceRepr, MethodsPBCRepr)):

    def convert_from_to(_, v, llops):
        return v

# ____________________________________________________________

PBCROOT = ootype.Instance('pbcroot', ootype.ROOT)

class MultipleFrozenPBCRepr(AbstractMultipleFrozenPBCRepr):
    """Representation selected for multiple non-callable pre-built constants."""
    def __init__(self, rtyper, access_set):
        self.rtyper = rtyper
        self.access_set = access_set
        self.lowleveltype = ootype.Instance('pbc', PBCROOT)
        self.pbc_cache = {}

    def _setup_repr(self):
        fields_list = self._setup_repr_fields()
        ootype.addFields(self.lowleveltype, dict(fields_list))

    def create_instance(self):
        return ootype.new(self.lowleveltype)

    def null_instance(self):
        return ootype.null(self.lowleveltype)

    def getfield(self, vpbc, attr, llops):
        mangled_name, r_value = self.fieldmap[attr]
        cmangledname = inputconst(ootype.Void, mangled_name)
        return llops.genop('oogetfield', [vpbc, cmangledname],
                           resulttype = r_value)

class MultipleUnrelatedFrozenPBCRepr(AbstractMultipleUnrelatedFrozenPBCRepr):
    """Representation selected for multiple non-callable pre-built constants
    with no common access set."""

    lowleveltype = PBCROOT

    def convert_pbc(self, pbc):
        if ootype.typeOf(pbc) != PBCROOT:
            pbc = ootype.ooupcast(PBCROOT, pbc)
        return pbc

    def create_instance(self):
        return ootype.new(PBCROOT)

    def null_instance(self):
        return ootype.null(PBCROOT)

class __extend__(pairtype(MultipleFrozenPBCRepr,
                          MultipleUnrelatedFrozenPBCRepr)):
    def convert_from_to((robj1, robj2), v, llops):
        return llops.genop('ooupcast', [v], resulttype=PBCROOT)
