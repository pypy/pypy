from pypy.rpython.ootypesystem.ootype import Signed, Record, new
from pypy.rpython.rrange import AbstractRangeRepr, AbstractRangeIteratorRepr

RANGE = Record({"start": Signed, "stop": Signed})
RANGEITER = Record({"next": Signed, "stop": Signed})

RANGEST = Record({"start": Signed, "stop": Signed, "step": Signed})
RANGESTITER = Record({"next": Signed, "stop": Signed, "step": Signed})

class RangeRepr(AbstractRangeRepr):

    RANGE = RANGE
    RANGEITER = RANGEITER
    RANGEST = RANGEST
    RANGESTITER = RANGESTITER

    getfield_opname = "oogetfield"

    def __init__(self, *args):
        AbstractRangeRepr.__init__(self, *args)
        self.ll_newrange = ll_newrange
        self.ll_newrangest = ll_newrangest

    def make_iterator_repr(self):
        return RangeIteratorRepr(self)


def ll_newrange(_RANGE, start, stop):
    l = new(RANGE)
    l.start = start
    l.stop = stop
    return l

def ll_newrangest(start, stop, step):
    if step == 0:
        raise ValueError
    l = new(RANGEST)
    l.start = start
    l.stop = stop
    l.step = step
    return l


class RangeIteratorRepr(AbstractRangeIteratorRepr):

    def __init__(self, *args):
        AbstractRangeIteratorRepr.__init__(self, *args)
        self.ll_rangeiter = ll_rangeiter

def ll_rangeiter(ITER, rng):
    iter = new(ITER)
    iter.next = rng.start
    iter.stop = rng.stop
    if ITER is RANGESTITER:
        iter.step = rng.step
    return iter

