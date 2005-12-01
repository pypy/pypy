from pypy.rpython.rpbc import AbstractClassesPBCRepr, AbstractMethodsPBCRepr
from pypy.rpython.rpbc import get_concrete_calltable
from pypy.rpython.rclass import rtype_new_instance
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rclass import ClassRepr, InstanceRepr, mangle
from pypy.rpython.ootypesystem.rclass import rtype_classes_is_
from pypy.annotation.pairtype import pairtype

class ClassesPBCRepr(AbstractClassesPBCRepr):
    def rtype_simple_call(self, hop):
        if self.lowleveltype is not ootype.Void:
            raise NotImplementedError()

        classdef = hop.s_result.classdef
        v_instance = rtype_new_instance(hop.rtyper, classdef, hop.llops)
        return v_instance

class MethodImplementations(object):

    def __init__(self, rtyper, methdescs):
        samplemdesc = methdescs.iterkeys().next()
        concretetable, uniquerows = get_concrete_calltable(rtyper,
                                             samplemdesc.funcdesc.getcallfamily())
        self._uniquerows = uniquerows
        if len(uniquerows) == 1:
            row = uniquerows[0]
            sample_as_static_meth = row.itervalues().next()
            SM = ootype.typeOf(sample_as_static_meth)
            M = ootype.Meth(SM.ARGS[1:], SM.RESULT) # cut self
            self.lowleveltype = M
        else:
            XXX_later

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

    def get_impl(self, name, methdesc):
        M = self.lowleveltype
        if methdesc is None:
            return ootype.meth(M, _name=name, abstract=True)
        else:
            impl_graph = self._uniquerows[0][methdesc.funcdesc].graph
            return ootype.meth(M, _name=name, graph=impl_graph)
    

class MethodsPBCRepr(AbstractMethodsPBCRepr):

    def __init__(self, rtyper, s_pbc):
        AbstractMethodsPBCRepr.__init__(self, rtyper, s_pbc)

    def rtype_simple_call(self, hop):
        vlist = hop.inputargs(self, *hop.args_r[1:])
        mangled = mangle(self.methodname)
        cname = hop.inputconst(ootype.Void, mangled)
        return hop.genop("oosend", [cname]+vlist,
                         resulttype = hop.r_result.lowleveltype)

        

class __extend__(pairtype(InstanceRepr, MethodsPBCRepr)):

    def convert_from_to(_, v, llops):
        return v


class __extend__(pairtype(ClassRepr, ClassesPBCRepr)):
    rtype_is_ = rtype_classes_is_

class __extend__(pairtype(ClassesPBCRepr, ClassRepr)):
    rtype_is_ = rtype_classes_is_
