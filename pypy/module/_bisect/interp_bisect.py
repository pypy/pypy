from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec


@unwrap_spec(lo=int, hi=int)
def bisect_left(space, w_a, w_x, lo=0, hi=-1):
    """Return the index where to insert item x in list a, assuming a is sorted.

The return value i is such that all e in a[:i] have e < x, and all e in
a[i:] have e >= x.  So if x already appears in the list, i points just
before the leftmost x already there.

Optional args lo (default 0) and hi (default len(a)) bound the
slice of a to be searched."""
    if lo < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("lo must be non-negative"))
    if hi == -1:
        hi = space.len_w(w_a)
    while lo < hi:
        mid = (lo + hi) >> 1
        w_litem = space.getitem(w_a, space.wrap(mid))
        if space.is_true(space.lt(w_litem, w_x)):
            lo = mid + 1
        else:
            hi = mid
    return space.wrap(lo)


@unwrap_spec(lo=int, hi=int)
def bisect_right(space, w_a, w_x, lo=0, hi=-1):
    """Return the index where to insert item x in list a, assuming a is sorted.

The return value i is such that all e in a[:i] have e <= x, and all e in
a[i:] have e > x.  So if x already appears in the list, i points just
beyond the rightmost x already there

Optional args lo (default 0) and hi (default len(a)) bound the
slice of a to be searched."""
    if lo < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("lo must be non-negative"))
    if hi == -1:
        hi = space.len_w(w_a)
    while lo < hi:
        mid = (lo + hi) >> 1
        w_litem = space.getitem(w_a, space.wrap(mid))
        if space.is_true(space.lt(w_x, w_litem)):
            hi = mid
        else:
            lo = mid + 1
    return space.wrap(lo)
