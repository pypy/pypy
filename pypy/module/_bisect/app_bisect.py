from _bisect import bisect_left, bisect_right


def insort_left(a, x, lo=0, hi=-1):
    """Insert item x in list a, and keep it sorted assuming a is sorted.

If x is already in a, insert it to the left of the leftmost x.

Optional args lo (default 0) and hi (default len(a)) bound the
slice of a to be searched."""
    n = bisect_left(a, x, lo, hi)
    a.insert(n, x)


def insort_right(a, x, lo=0, hi=-1):
    """Insert item x in list a, and keep it sorted assuming a is sorted.

If x is already in a, insert it to the right of the rightmost x.

Optional args lo (default 0) and hi (default len(a)) bound the
slice of a to be searched."""
    n = bisect_right(a, x, lo, hi)
    a.insert(n, x)
