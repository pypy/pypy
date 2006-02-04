from pypy.annotation.pairtype import pairtype
from pypy.jit.hintrtyper import HintTypeSystem
from pypy.jit.hintmodel import SomeLLAbstractConstant
from pypy.rpython.rmodel import Repr

class __extend__(pairtype(HintTypeSystem, SomeLLAbstractConstant)):

    def rtyper_makerepr((ts, hs_c), rtyper):
        if hs_c.is_fixed() or hs_c.eager_concrete:
            return LLFixedConstantRepr(hs_c.concretetype)
        else:
            XXX

    def rtyper_makekey((ts, hs_c), rtyper):
        fixed = hs_c.is_fixed() or hs_c.eager_concrete
        return hs_c.__class__, fixed, hs_c.concretetype

class LLFixedConstantRepr(Repr):

    def __init__(self, lowleveltype):
        self.lowleveltype = lowleveltype

#...
#
#    def rtype_int_add(_, hop):
#        hop.inputargs(
