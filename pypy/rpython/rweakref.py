from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem import lltype, llmemory


class __extend__(annmodel.SomeLLWeakRef):
    def rtyper_makerepr(self, rtyper):
        return LLWeakRefRepr()
    def rtyper_makekey(self):
        return self.__class__,


class LLWeakRefRepr(Repr):
    lowleveltype = llmemory.WeakRef
