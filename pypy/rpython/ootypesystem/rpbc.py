from pypy.rpython.rpbc import AbstractClassesPBCRepr, AbstractMethodsPBCRepr
from pypy.rpython.rclass import rtype_new_instance
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rclass import InstanceRepr
from pypy.annotation.pairtype import pairtype

class ClassesPBCRepr(AbstractClassesPBCRepr):
    def rtype_simple_call(self, hop):
        if self.lowleveltype is not ootype.Void:
            raise NotImplementedError()

        klass = self.s_pbc.const
        v_instance = rtype_new_instance(hop.rtyper, klass, hop.llops)
        return v_instance


class MethodsPBCRepr(AbstractMethodsPBCRepr):

    def rtype_simple_call(self, hop):
        vlist = hop.inputargs(self, *hop.args_r[1:])
        cname = hop.inputconst(ootype.Void, self.methodname)
        return hop.genop("oosend", [cname]+vlist,
                         resulttype = hop.r_result.lowleveltype)

        

class __extend__(pairtype(InstanceRepr, MethodsPBCRepr)):

    def convert_from_to(_, v, llops):
        return v
