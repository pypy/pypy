from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem.lltype import Signed, Void
from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel
from pypy.rpython.error import TyperError

class AbstractSliceRepr(Repr):
    pass


def select_slice_repr(self):
    # Select which one of the three prebuilt reprs to use.
    # Return a name.
    if not self.step.is_constant() or self.step.const not in (None, 1):
        raise TyperError("only supports slices with step 1")
    if (self.start.is_constant() and self.start.const in (None, 0) and
        self.stop.is_constant() and self.stop.const == -1):
        return "minusone_slice_repr"    # [:-1]
    if isinstance(self.start, annmodel.SomeInteger):
        if not self.start.nonneg:
            raise TyperError("slice start must be proved non-negative")
    if isinstance(self.stop, annmodel.SomeInteger):
        if not self.stop.nonneg:
            raise TyperError("slice stop must be proved non-negative")
    if self.stop.is_constant() and self.stop.const is None:
        return "startonly_slice_repr"
    else:
        return "startstop_slice_repr"

class __extend__(annmodel.SomeSlice):
    def rtyper_makerepr(self, rtyper):
        return getattr(rtyper.type_system.rslice, select_slice_repr(self))
        
    def rtyper_makekey(self):
        return self.__class__, select_slice_repr(self)


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
    if (isinstance(v_start, Constant) and v_start.value == 0 and
        isinstance(v_stop, Constant) and v_stop.value == -1):
        # [:-1] slice
        return hop.inputconst(Void, slice(None,-1))
    if isinstance(v_stop, Constant) and v_stop.value is None:
        # start-only slice
        # NB. cannot just return v_start in case it is a constant
        return hop.genop('same_as', [v_start],
            resulttype=hop.rtyper.type_system.rslice.startonly_slice_repr)
    else:
        # start-stop slice
        return hop.gendirectcall(hop.rtyper.type_system.rslice.ll_newslice,
                                 v_start, v_stop)
