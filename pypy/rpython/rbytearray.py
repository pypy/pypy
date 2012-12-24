
from pypy.rpython.rmodel import Repr
from pypy.annotation import model as annmodel

class AbstractByteArrayRepr(Repr):
    pass

class __extend__(annmodel.SomeByteArray):
    def rtyper_makekey(self):
        return self.__class__,

    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rbytearray.bytearray_repr
