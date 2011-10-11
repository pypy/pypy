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

def any(seq):
    """any(iterable) -> bool

Return True if bool(x) is True for any x in the iterable."""
    for x in seq:
        if x:
            return True
    return False

def all(seq):
    """all(iterable) -> bool

Return True if bool(x) is True for all values x in the iterable."""
    for x in seq:
        if not x:
            return False
    return True

def sum(sequence, start=0):
    """sum(sequence[, start]) -> value

Returns the sum of a sequence of numbers (NOT strings) plus the value
of parameter 'start' (which defaults to 0).  When the sequence is
empty, returns start."""
    if isinstance(start, basestring):
        raise TypeError("sum() can't sum strings")
    last = start
    for x in sequence:
        # Very intentionally *not* +=, that would have different semantics if
        # start was a mutable type, such as a list
        last = last + x
    return last

def map(func, *collections):
    """map(function, sequence[, sequence, ...]) -> list

Return a list of the results of applying the function to the items of
the argument sequence(s).  If more than one sequence is given, the
function is called with an argument list consisting of the corresponding
item of each sequence, substituting None for missing values when not all
sequences have the same length.  If the function is None, return a list of
the items of the sequence (or a list of tuples if more than one sequence)."""
    if not collections:
        raise TypeError("map() requires at least two arguments")
    num_collections = len(collections)
    none_func = func is None
    if num_collections == 1:
        if none_func:
            return list(collections[0])
        else:
            # Special case for the really common case of a single collection,
            # this can be eliminated if we could unroll that loop that creates
            # `args` based on whether or not len(collections) was constant
            result = []
            for item in collections[0]:
                result.append(func(item))
            return result
    result = []
    # Pair of (iterator, has_finished)
    iterators = [(iter(seq), False) for seq in collections]
    while True:
        cont = False
        args = []
        for idx, (iterator, has_finished) in enumerate(iterators):
            val = None
            if not has_finished:
                try:
                    val = next(iterator)
                except StopIteration:
                    iterators[idx] = (None, True)
                else:
                    cont = True
            args.append(val)
        args = tuple(args)
        if cont:
            if none_func:
                result.append(args)
            else:
                result.append(func(*args))
        else:
            return result
