
def bisect_left(a, x):
    """Return the index in the sorted list 'a' of 'x'.  If 'x' is not in 'a',
    return the index where it can be inserted."""
    lo = 0
    hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if a[mid] < x: lo = mid+1
        else: hi = mid
    return lo

def bisect_right(a, x):
    lo = 0
    hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if x < a[mid]: hi = mid
        else: lo = mid+1
    return lo

# a copy of the above, but compares the first item of a tuple only
def bisect_left_tuple(a, x):
    lo = 0
    hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if a[mid][0] < x: lo = mid+1
        else: hi = mid
    return lo

def bisect_right_tuple(a, x):
    lo = 0
    hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if x < a[mid][0]: hi = mid
        else: lo = mid+1
    return lo
