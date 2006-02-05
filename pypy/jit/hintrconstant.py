from pypy.annotation.pairtype import pairtype
from pypy.jit.hintrtyper import HintTypeSystem
from pypy.jit.hintmodel import SomeLLAbstractConstant
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem import lltype

class __extend__(pairtype(HintTypeSystem, SomeLLAbstractConstant)):

    def rtyper_makerepr((ts, hs_c), rtyper):
        if hs_c.is_fixed() or hs_c.eager_concrete:
            return getfixedrepr(rtyper, hs_c.concretetype)
        else:
            XXX

    def rtyper_makekey((ts, hs_c), rtyper):
        fixed = hs_c.is_fixed() or hs_c.eager_concrete
        return hs_c.__class__, fixed, hs_c.concretetype


class LLFixedConstantRepr(Repr):

    def __init__(self, lowleveltype):
        self.lowleveltype = lowleveltype

    def rtype_hint(self, hop):
        # discard the hint operation
        return hop.inputarg(self, arg=0)


class __extend__(pairtype(LLFixedConstantRepr, LLFixedConstantRepr)):

    def rtype_int_add(_, hop):
        vlist = hop.inputargs(fixed_signed_repr, fixed_signed_repr)
        return hop.genop('int_add', vlist, resulttype=lltype.Signed)

# ____________________________________________________________

def getfixedrepr(rtyper, lowleveltype):
    try:
        return rtyper._fixed_reprs[lowleveltype]
    except KeyError:
        r = LLFixedConstantRepr(lowleveltype)
        rtyper._fixed_reprs[lowleveltype] = r
        return r

fixed_signed_repr = LLFixedConstantRepr(lltype.Signed)

# collect the global precomputed reprs
PRECOMPUTED_FIXED_REPRS = {}
for _r in globals().values():
    if isinstance(_r, LLFixedConstantRepr):
        PRECOMPUTED_FIXED_REPRS[_r.lowleveltype] = _r
