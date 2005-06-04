from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr
from pypy.rpython.lltype import *

# ____________________________________________________________
#
#  Concrete implementation of RPython lists that are returned by range()
#  and never mutated afterwards:
#
#    struct range {
#        Signed start, stop;    // step is always constant
#    }

RANGE = GcStruct("range", ("start", Signed), ("stop", Signed))


class RangeRepr(Repr):
    lowlevelrepr = GcPtr(RANGE)

    def __init__(self, step):
        self.step = step

    def rtype_len(self, hop):
        v_rng, = hop.inputargs(self)
        cstep = hop.inputconst(Signed, self.step)
        return hop.gendirectcall(ll_rangelen, v_rng, cstep)

    def make_iterator_repr(self):
        return riter.RangeIteratorRepr(self)

class __extend__(pairtype(RangeRepr, IntegerRepr)):

    def rtype_getitem((r_rng, r_int), hop):
        v_lst, v_index = hop.inputargs(r_lst, Signed)
        cstep = hop.inputconst(Signed, self.step)
        if hop.args_s[1].nonneg:
            llfn = ll_rangeitem_nonneg
        else:
            llfn = ll_rangeitem
        return hop.gendirectcall(llfn, v_lst, v_index, cstep)

# ____________________________________________________________
#
#  Low-level methods.

def ll_rangelen(l, step):
    if step > 0:
        result = (l.stop - l.start + (step-1)) // step
    else:
        result = (l.start - l.stop - (step+1)) // (-step)
    if result < 0:
        result = 0
    return result

def ll_rangeitem_nonneg(l, i, step):
    return l.start + i*step

def ll_rangeitem(l, i, step):
    if i<0:
        # XXX ack. cannot call ll_rangelen() here for now :-(
        if step > 0:
            length = (l.stop - l.start + (step-1)) // step
        else:
            length = (l.start - l.stop - (step+1)) // (-step)
        #assert length >= 0
        i += length
    return l.start + i*step

# ____________________________________________________________
#
#  Irregular operations.

def ll_newrange(start, stop):
    l = malloc(RANGE)
    l.start = start
    l.stop = stop
    return l

def rtype_builtin_range(hop):
    vstep = hop.inputconst(Signed, 1)
    if hop.nb_args == 1:
        vstart = hop.inputconst(Signed, 0)
        vstop, = hop.inputargs(Signed)
    elif hop.nb_args == 2:
        vstart, vstop = hop.inputargs(Signed, Signed)
    else:
        vstart, vstop, vstep = hop.inputargs(Signed, Signed, Signed)
        assert isinstance(vstep, Constant)

    if isinstance(hop.r_result, RangeRepr):
        return hop.gendirectcall(ll_newrange, vstart, vstop)
    else:
        # cannot build a RANGE object, needs a real list
        raise TyperError("range() result used as a normal list: "
                         "XXX not implemented")
        #return hop.gendirectcall(ll_range2list, vstart, vstop, vstep)
