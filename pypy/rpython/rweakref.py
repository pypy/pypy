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

# ____________________________________________________________
#
# RPython-level weakrefs

class __extend__(annmodel.SomeWeakRef):
    def rtyper_makerepr(self, rtyper):
        return WeakRefRepr()
    def rtyper_makekey(self):
        return self.__class__,


class WeakRefRepr(Repr):
    lowleveltype = llmemory.WeakRef

    def rtype_simple_call(self, hop):
        v_wref, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.genop('weakref_deref', [v_wref], resulttype=hop.r_result)
