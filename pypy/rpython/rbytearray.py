
from pypy.rpython.rmodel import Repr
from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pairtype
from pypy.rpython.rstr import AbstractStringRepr

class AbstractByteArrayRepr(Repr):
    pass

class __extend__(pairtype(AbstractByteArrayRepr, AbstractByteArrayRepr)):
    def rtype_add((r_b1, r_b2), hop):
        xxx

class __extend__(pairtype(AbstractByteArrayRepr, AbstractStringRepr)):
    def rtype_add((r_b1, r_s2), hop):
        str_repr = r_s2.repr
        if hop.s_result.is_constant():
            return hop.inputconst(r_b1, hop.s_result.const)
        v_b1, v_str2 = hop.inputargs(r_b1, str_repr)
        return hop.gendirectcall(r_b1.ll.ll_strconcat, v_b1, v_str2)

class __extend__(pairtype(AbstractStringRepr, AbstractByteArrayRepr)):
    def rtype_add((r_s2, r_b1), hop):
        xxx

class __extend__(annmodel.SomeByteArray):
    def rtyper_makekey(self):
        return self.__class__,

    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rbytearray.bytearray_repr
