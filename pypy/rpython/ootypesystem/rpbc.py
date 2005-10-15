from pypy.rpython.rpbc import AbstractClassesPBCRepr
from pypy.rpython.rclass import rtype_new_instance
from pypy.rpython.ootypesystem import ootype

class ClassesPBCRepr(AbstractClassesPBCRepr):
    def rtype_simple_call(self, hop):
        if self.lowleveltype is not ootype.Void:
            raise NotImplementedError()

        klass = self.s_pbc.const
        v_instance = rtype_new_instance(hop.rtyper, klass, hop.llops)
        return v_instance
