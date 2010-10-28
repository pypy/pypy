from pypy.interpreter.gateway import ObjSpace, W_Root


def bisect_left(space, w_a, w_x, lo=0, hi=-1):
    """Return the index where to insert item x in list a, assuming a is sorted.

The return value i is such that all e in a[:i] have e < x, and all e in
a[i:] have e >= x.  So if x already appears in the list, i points just
before the leftmost x already there.

Optional args lo (default 0) and hi (default len(a)) bound the
slice of a to be searched."""
    if hi == -1:
        hi = space.int_w(space.len(w_a))
    while lo < hi:
        mid = (lo + hi) >> 1
        w_litem = space.getitem(w_a, space.wrap(mid))
        if space.is_true(space.lt(w_litem, w_x)):
            lo = mid + 1
        else:
            hi = mid
    return space.wrap(lo)
bisect_left.unwrap_spec = [ObjSpace, W_Root, W_Root, int, int]


def bisect_right(space, w_a, w_x, lo=0, hi=-1):
    """Return the index where to insert item x in list a, assuming a is sorted.

The return value i is such that all e in a[:i] have e <= x, and all e in
a[i:] have e > x.  So if x already appears in the list, i points just
beyond the rightmost x already there

Optional args lo (default 0) and hi (default len(a)) bound the
slice of a to be searched."""
    if hi == -1:
        hi = space.int_w(space.len(w_a))
    while lo < hi:
        mid = (lo + hi) >> 1
        w_litem = space.getitem(w_a, space.wrap(mid))
        if space.is_true(space.lt(w_x, w_litem)):
            hi = mid
        else:
            lo = mid + 1
    return space.wrap(lo)
bisect_right.unwrap_spec = [ObjSpace, W_Root, W_Root, int, int]
