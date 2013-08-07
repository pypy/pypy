import weakref
from rpython.annotator import model as annmodel
from rpython.flowspace.model import Constant
from rpython.rtyper.error import TyperError
from rpython.rtyper.rmodel import Repr
from rpython.rtyper.lltypesystem import lltype, llmemory

# ____________________________________________________________
#
# RTyping of RPython-level weakrefs

class __extend__(annmodel.SomeWeakRef):
    def rtyper_makerepr(self, rtyper):
        return WeakRefRepr(rtyper)

    def rtyper_makekey(self):
        return self.__class__,

class WeakRefRepr(Repr):
    lowleveltype = llmemory.WeakRefPtr
    dead_wref = llmemory.dead_wref
    null_wref = lltype.nullptr(llmemory.WeakRef)

    def __init__(self, rtyper):
        self.rtyper = rtyper
        if not rtyper.getconfig().translation.rweakref:
            raise TyperError("RPython-level weakrefs are not supported by "
                             "this backend or GC policy")

    def convert_const(self, value):
        if value is None:
            return self.null_wref

        assert isinstance(value, weakref.ReferenceType)
        instance = value()
        bk = self.rtyper.annotator.bookkeeper
        # obscure!  if the annotator hasn't seen this object before,
        # we don't want to look at it now (confusion tends to result).
        if instance is None or not bk.have_seen(instance):
            return self.dead_wref
        else:
            repr = self.rtyper.bindingrepr(Constant(instance))
            llinstance = repr.convert_const(instance)
            return self._weakref_create(llinstance)


    def rtype_simple_call(self, hop):
        v_wref, = hop.inputargs(self)
        hop.exception_cannot_occur()
        if hop.r_result.lowleveltype is lltype.Void: # known-to-be-dead weakref
            return hop.inputconst(lltype.Void, None)
        else:
            return hop.genop('weakref_deref', [v_wref],
                             resulttype=hop.r_result)

    def _weakref_create(self, llinstance):
        return llmemory.weakref_create(llinstance)
