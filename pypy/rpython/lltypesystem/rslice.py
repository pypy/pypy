from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.lltypesystem.lltype import \
     GcStruct, Signed, Ptr, Void, malloc

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


class SliceRepr(AbstractSliceRepr):
    pass

startstop_slice_repr = SliceRepr()
startstop_slice_repr.lowleveltype = Ptr(SLICE)
startonly_slice_repr = SliceRepr()
startonly_slice_repr.lowleveltype = Signed
minusone_slice_repr = SliceRepr()
minusone_slice_repr.lowleveltype = Void    # only for [:-1]

# ____________________________________________________________

def ll_newslice(start, stop):
    s = malloc(SLICE)
    s.start = start
    s.stop = stop
    return s

