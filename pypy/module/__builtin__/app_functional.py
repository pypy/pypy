"""
Plain Python definition of the builtin functions oriented towards
functional programming.
"""

# ____________________________________________________________

def apply(function, args=(), kwds={}):
    """call a function (or other callable object) and return its result"""
    return function(*args, **kwds)

# ____________________________________________________________

def sorted(lst, cmp=None, key=None, reverse=None):
    "sorted(iterable, cmp=None, key=None, reverse=False) --> new sorted list"
    sorted_lst = list(lst)
    sorted_lst.sort(cmp, key, reverse)
    return sorted_lst
