from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.lltypesystem.lltype import Void, Signed
from pypy.rpython.ootypesystem import ootype

SLICE = ootype.Instance('Slice', ootype.ROOT, {'start': Signed, 'stop': Signed})

class SliceRepr(AbstractSliceRepr):
    pass

startstop_slice_repr = SliceRepr()
startstop_slice_repr.lowleveltype = SLICE
startonly_slice_repr = SliceRepr()
startonly_slice_repr.lowleveltype = Signed
minusone_slice_repr = SliceRepr()
minusone_slice_repr.lowleveltype = Void    # only for [:-1]

# ____________________________________________________________

def ll_newslice(start, stop):
    s = ootype.new(SLICE)
    s.start = start
    s.stop = stop
    return s

