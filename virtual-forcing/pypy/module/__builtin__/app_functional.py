"""
Plain Python definition of the builtin functions oriented towards
functional programming.
"""

# ____________________________________________________________

def apply(function, args=(), kwds={}):
    """call a function (or other callable object) and return its result"""
    return function(*args, **kwds)

# ____________________________________________________________

"""
The following is a nice example of collaboration between
interp-level and app-level.
range is primarily implemented in functional.py for the integer case.
On every error or different data types, it redirects to the applevel
implementation below. functional.py uses this source via the inspect
module and uses gateway.applevel. This is also an alternative to
writing longer functions in strings.
"""

def range(x, y=None, step=1):
    """ returns a list of integers in arithmetic position from start (defaults
        to zero) to stop - 1 by step (defaults to 1).  Use a negative step to
        get a list in decending order."""


    if y is None: 
        start = 0
        stop = x
    else:
        start = x
        stop = y

    if not isinstance(start, (int, long)):
        raise TypeError('range() integer start argument expected, got %s' % type(start))
    if not isinstance(stop, (int, long)):
        raise TypeError('range() integer stop argument expected, got %s' % type(stop))
    if not isinstance(step, (int, long)):
        raise TypeError('range() integer step argument expected, got %s' % type(step))

    if step == 0:
        raise ValueError, 'range() arg 3 must not be zero'

    elif step > 0:
        if stop <= start: # no work for us
            return []
        howmany = (stop - start + step - 1)/step

    else:  # step must be < 0, or we would have raised ValueError
        if stop >= start: # no work for us
            return []
        howmany = (start - stop - step  - 1)/-step

    arr = [None] * howmany  # this is to avoid using append.

    i = start
    n = 0
    while n < howmany:
        arr[n] = i
        i += step
        n += 1

    return arr

# ____________________________________________________________

def sorted(lst, cmp=None, key=None, reverse=None):
    "sorted(iterable, cmp=None, key=None, reverse=False) --> new sorted list"
    sorted_lst = list(lst)
    sorted_lst.sort(cmp, key, reverse)
    return sorted_lst


