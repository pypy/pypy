from pypy.rpython.lltypesystem.lltype import Ptr, GcStruct, Signed, malloc, Void
from pypy.rpython.rrange import AbstractRangeRepr, AbstractRangeIteratorRepr

# ____________________________________________________________
#
#  Concrete implementation of RPython lists that are returned by range()
#  and never mutated afterwards:
#
#    struct range {
#        Signed start, stop;    // step is always constant
#    }
#
#    struct rangest {
#        Signed start, stop, step;    // rare case, for completeness
#    }

RANGE = GcStruct("range", ("start", Signed), ("stop", Signed))
RANGEITER = GcStruct("range", ("next", Signed), ("stop", Signed))

RANGEST = GcStruct("range", ("start", Signed), ("stop", Signed),("step", Signed))
RANGESTITER = GcStruct("range", ("next", Signed), ("stop", Signed), ("step", Signed))

class RangeRepr(AbstractRangeRepr):

    RANGE = Ptr(RANGE)
    RANGEITER = Ptr(RANGEITER)

    RANGEST = Ptr(RANGEST)
    RANGESTITER = Ptr(RANGESTITER)

    getfield_opname = "getfield"

    def __init__(self, *args):
        AbstractRangeRepr.__init__(self, *args)
        self.ll_newrange = ll_newrange
        self.ll_newrangest = ll_newrangest

    def make_iterator_repr(self):
        return RangeIteratorRepr(self)


def ll_newrange(start, stop):
    l = malloc(RANGE)
    l.start = start
    l.stop = stop
    return l

def ll_newrangest(start, stop, step):
    if step == 0:
        raise ValueError
    l = malloc(RANGEST)
    l.start = start
    l.stop = stop
    l.step = step
    return l


class RangeIteratorRepr(AbstractRangeIteratorRepr):

    def __init__(self, *args):
        AbstractRangeIteratorRepr.__init__(self, *args)
        self.ll_rangeiter = ll_rangeiter

def ll_rangeiter(ITERPTR, rng):
    iter = malloc(ITERPTR.TO)
    iter.next = rng.start
    iter.stop = rng.stop
    if ITERPTR.TO is RANGESTITER:
        iter.step = rng.step
    return iter

