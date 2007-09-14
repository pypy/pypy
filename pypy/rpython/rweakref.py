import weakref
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype

# ____________________________________________________________
#
# RTyping of RPython-level weakrefs

class __extend__(annmodel.SomeWeakRef):
    def rtyper_makerepr(self, rtyper):
        if rtyper.type_system.name == 'lltypesystem':
            return LLWeakRefRepr(rtyper)
        else:
            return OOWeakRefRepr(rtyper)
    def rtyper_makekey(self):
        return self.__class__,

class BaseWeakRefRepr(Repr):

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

    def _weakref_create(self, llinstance):
        raise NotImplementedError

class LLWeakRefRepr(BaseWeakRefRepr):
    lowleveltype = llmemory.WeakRefPtr
    dead_wref = llmemory.dead_wref
    null_wref = lltype.nullptr(llmemory.WeakRef)

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

class OOWeakRefRepr(BaseWeakRefRepr):
    lowleveltype = ootype.WeakReference
    dead_wref = ootype.dead_wref
    null_wref = ootype.null(ootype.WeakReference)
    
    def rtype_simple_call(self, hop):
        v_wref, = hop.inputargs(self)
        cname = hop.inputconst(ootype.Void, 'll_deref')
        hop.exception_cannot_occur()
        if hop.r_result.lowleveltype is lltype.Void: # known-to-be-dead weakref
            return hop.inputconst(lltype.Void, None)
        else:
            v_deref = hop.genop('oosend', [cname, v_wref],
                                resulttype=ootype.ROOT)
            return hop.genop('oodowncast', [v_deref], resulttype=hop.r_result)

    def _weakref_create(self, llinstance):
        return ootype.ooweakref_create(llinstance)
