import weakref
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.lltypesystem import lltype, llmemory

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

    def __init__(self, rtyper):
        self.rtyper = rtyper
        if not rtyper.getconfig().translation.rweakref:
            raise TyperError("RPython-level weakrefs are not supported by "
                             "this backend or GC policy")

    def rtype_simple_call(self, hop):
        v_wref, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.genop('weakref_deref', [v_wref], resulttype=hop.r_result)

    def convert_const(self, value):
        assert isinstance(value, weakref.ReferenceType)
        instance = value()
        bk = self.rtyper.annotator.bookkeeper
        # obscure!  if the annotator hasn't seen this object before,
        # we don't want to look at it now (confusion tends to result).
        if instance is None or not bk.have_seen(instance):
            return llmemory.dead_wref
        else:
            repr = self.rtyper.bindingrepr(Constant(instance))
            llinstance = repr.convert_const(instance)
            return llmemory.weakref_create(llinstance)
