from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr, IteratorRepr
from pypy.rpython.lltype import Ptr, GcStruct, Signed, malloc, Void
from pypy.objspace.flow.model import Constant
from pypy.rpython.rlist import ll_newlist, dum_nocheck, dum_checkidx

# ____________________________________________________________
#
#  Concrete implementation of RPython lists that are returned by range()
#  and never mutated afterwards:
#
#    struct range {
#        Signed start, stop;    // step is always constant
#    }

RANGE = GcStruct("range", ("start", Signed), ("stop", Signed))
RANGEITER = GcStruct("range", ("next", Signed), ("stop", Signed))


class RangeRepr(Repr):
    lowleveltype = Ptr(RANGE)

    def __init__(self, step):
        self.step = step

    def rtype_len(self, hop):
        v_rng, = hop.inputargs(self)
        cstep = hop.inputconst(Signed, self.step)
        return hop.gendirectcall(ll_rangelen, v_rng, cstep)

    def make_iterator_repr(self):
        return RangeIteratorRepr(self)

class __extend__(pairtype(RangeRepr, IntegerRepr)):

    def rtype_getitem((r_rng, r_int), hop):
        from pypy.rpython.rlist import dum_nocheck, dum_checkidx
        if hop.has_implicit_exception(IndexError):
            spec = dum_checkidx
        else:
            spec = dum_nocheck
        v_func = hop.inputconst(Void, spec)
        v_lst, v_index = hop.inputargs(r_rng, Signed)
        cstep = hop.inputconst(Signed, r_rng.step)
        if hop.args_s[1].nonneg:
            llfn = ll_rangeitem_nonneg
        else:
            llfn = ll_rangeitem
        hop.exception_is_here()
        return hop.gendirectcall(llfn, v_func, v_lst, v_index, cstep)

# ____________________________________________________________
#
#  Low-level methods.

def _ll_rangelen(start, stop, step):
    if step > 0:
        result = (stop - start + (step-1)) // step
    else:
        result = (start - stop - (step+1)) // (-step)
    if result < 0:
        result = 0
    return result

def ll_rangelen(l, step):
    return _ll_rangelen(l.start, l.stop, step)

def ll_rangeitem_nonneg(func, l, index, step):
    if func is dum_checkidx and index >= _ll_rangelen(l.start, l.stop, step):
        raise IndexError
    return l.start + index * step

def ll_rangeitem(func, l, index, step):
    if func is dum_checkidx:
        length = _ll_rangelen(l.start, l.stop, step)
        if index < 0:
            index += length
        if index < 0 or index >= length:
            raise IndexError
    else:
        if index < 0:
            length = _ll_rangelen(l.start, l.stop, step)
            index += length
    return l.start + index * step

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
        r_list = hop.r_result
        c1 = hop.inputconst(Void, r_list.lowleveltype)
        return hop.gendirectcall(ll_range2list, c1, vstart, vstop, vstep)

rtype_builtin_xrange = rtype_builtin_range

def ll_range2list(LISTPTR, start, stop, step):
    length = _ll_rangelen(start, stop, step)
    l = ll_newlist(LISTPTR, length)
    idx = 0
    items = l.items
    while idx < length:
        items[idx] = start
        start += step
        idx += 1
    return l

# ____________________________________________________________
#
#  Iteration.

class RangeIteratorRepr(IteratorRepr):
    lowleveltype = Ptr(RANGEITER)

    def __init__(self, r_rng):
        self.r_rng = r_rng

    def newiter(self, hop):
        v_rng, = hop.inputargs(self.r_rng)
        citerptr = hop.inputconst(Void, self.lowleveltype)
        return hop.gendirectcall(ll_rangeiter, citerptr, v_rng)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
        cstep = hop.inputconst(Signed, self.r_rng.step)
        if self.r_rng.step > 0:
            llfn = ll_rangenext_up
        else:
            llfn = ll_rangenext_down
        hop.has_implicit_exception(StopIteration) # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(llfn, v_iter, cstep)

def ll_rangeiter(ITERPTR, rng):
    iter = malloc(ITERPTR.TO)
    iter.next = rng.start
    iter.stop = rng.stop
    return iter

def ll_rangenext_up(iter, step):
    next = iter.next
    if next >= iter.stop:
        raise StopIteration
    iter.next = next + step
    return next

def ll_rangenext_down(iter, step):
    next = iter.next
    if next <= iter.stop:
        raise StopIteration
    iter.next = next + step
    return next
