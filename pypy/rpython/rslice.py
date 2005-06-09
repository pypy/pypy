from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import *
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr
import sys

# ____________________________________________________________
#
#  Concrete implementation of RPython slice objects:
#
#  - if stop is None, use only a Signed
#  - if stop is not None:
#
#      struct slice {
#          Signed start;
#          Signed stop;
#          //     step is always 1
#      }

SLICE = GcStruct("slice", ("start", Signed), ("stop", Signed))


class __extend__(annmodel.SomeSlice):
    def rtyper_makerepr(self, rtyper):
        if not self.step.is_constant() or self.step.const not in (None, 1):
            raise TyperError("only supports slices with step 1")
        if isinstance(self.start, annmodel.SomeInteger):
            if not self.start.nonneg:
                raise TyperError("slice start must be proved non-negative")
        if isinstance(self.stop, annmodel.SomeInteger):
            if not self.stop.nonneg:
                raise TyperError("slice stop must be proved non-negative")
        if self.stop.is_constant() and self.stop.const is None:
            return startonly_slice_repr
        else:
            return startstop_slice_repr
    def rtyper_makekey(self):
        return self.stop.rtyper_makekey(), self.step.rtyper_makekey()


class SliceRepr(Repr):
    pass

startstop_slice_repr = SliceRepr()
startstop_slice_repr.lowleveltype = Ptr(SLICE)
startonly_slice_repr = SliceRepr()
startonly_slice_repr.lowleveltype = Signed

# ____________________________________________________________

def ll_newslice(start, stop):
    s = malloc(SLICE)
    s.start = start
    s.stop = stop
    return s

def rtype_newslice(hop):
    sig = []
    for s in hop.args_s:
        if s.is_constant() and s.const is None:
            sig.append(Void)
        else:
            sig.append(Signed)
    v_start, v_stop, v_step = hop.inputargs(*sig)
    assert isinstance(v_step, Constant) and v_step.value in (None, 1)
    if isinstance(v_start, Constant) and v_start.value is None:
        v_start = hop.inputconst(Signed, 0)
    if isinstance(v_stop, Constant) and v_stop.value is None:
        # start-only slice
        # NB. cannot just return v_start in case it is a constant
        return hop.genop('same_as', [v_start], resulttype=startonly_slice_repr)
    else:
        # start-stop slice
        return hop.gendirectcall(ll_newslice, v_start, v_stop)
