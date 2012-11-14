"""
Plain Python definition of the builtin functions oriented towards
functional programming.
"""
from __future__ import with_statement
import operator
from __pypy__ import resizelist_hint, newlist_hint

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
        # Special case for the really common case of a single collection,
        # this can be eliminated if we could unroll that loop that creates
        # `args` based on whether or not len(collections) was constant
        seq = collections[0]
        with _ManagedNewlistHint(operator._length_hint(seq, 0)) as result:
            for item in seq:
                result.append(func(item))
            return result

    # Gather the iterators (pair of (iter, has_finished)) and guess the
    # result length (the max of the input lengths)
    iterators = []
    max_hint = 0
    for seq in collections:
        iterators.append((iter(seq), False))
        max_hint = max(max_hint, operator._length_hint(seq, 0))

    with _ManagedNewlistHint(max_hint) as result:
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

class _ManagedNewlistHint(object):
    """ Context manager returning a newlist_hint upon entry.

    Upon exit the list's underlying capacity will be cut back to match
    its length if necessary (incase the initial length_hint was too
    large).
    """

    def __init__(self, length_hint):
        self.length_hint = length_hint
        self.list = newlist_hint(length_hint)

    def __enter__(self):
        return self.list

    def __exit__(self, type, value, tb):
        if type is None:
            extended = len(self.list)
            if extended < self.length_hint:
                resizelist_hint(self.list, extended)

sentinel = object()

def reduce(func, sequence, initial=sentinel):
    """reduce(function, sequence[, initial]) -> value

Apply a function of two arguments cumulatively to the items of a sequence,
from left to right, so as to reduce the sequence to a single value.
For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5]) calculates
((((1+2)+3)+4)+5).  If initial is present, it is placed before the items
of the sequence in the calculation, and serves as a default when the
sequence is empty."""
    iterator = iter(sequence)
    if initial is sentinel:
        try:
            initial = next(iterator)
        except StopIteration:
            raise TypeError("reduce() of empty sequence with no initial value")
    result = initial
    for item in iterator:
        result = func(result, item)
    return result

def filter(func, seq):
    """filter(function or None, sequence) -> list, tuple, or string

Return those items of sequence for which function(item) is true.  If
function is None, return the items that are true.  If sequence is a tuple
or string, return the same type, else return a list."""
    if func is None:
        func = bool
    if isinstance(seq, str):
        return _filter_string(func, seq, str)
    elif isinstance(seq, unicode):
        return _filter_string(func, seq, unicode)
    elif isinstance(seq, tuple):
        return _filter_tuple(func, seq)
    with _ManagedNewlistHint(operator._length_hint(seq, 0)) as result:
        for item in seq:
            if func(item):
                result.append(item)
    return result

def _filter_string(func, string, str_type):
    if func is bool and type(string) is str_type:
        return string
    length = len(string)
    result = newlist_hint(length)
    for i in range(length):
        # You must call __getitem__ on the strings, simply iterating doesn't
        # work :/
        item = string[i]
        if func(item):
            if not isinstance(item, str_type):
                raise TypeError("__getitem__ returned a non-string type")
            result.append(item)
    return str_type().join(result)

def _filter_tuple(func, seq):
    length = len(seq)
    result = newlist_hint(length)
    for i in range(length):
        # Again, must call __getitem__, at least there are tests.
        item = seq[i]
        if func(item):
            result.append(item)
    return tuple(result)

def zip(*sequences):
    """zip(seq1 [, seq2 [...]]) -> [(seq1[0], seq2[0] ...), (...)]

Return a list of tuples, where each tuple contains the i-th element
from each of the argument sequences.  The returned list is truncated
in length to the length of the shortest argument sequence."""
    if not sequences:
        return []

    # Gather the iterators and guess the result length (the min of the
    # input lengths)
    iterators = []
    min_hint = -1
    for seq in sequences:
        iterators.append(iter(seq))
        hint = operator._length_hint(seq, min_hint)
        if min_hint == -1 or hint < min_hint:
            min_hint = hint
    if min_hint == -1:
        min_hint = 0

    with _ManagedNewlistHint(min_hint) as result:
        while True:
            try:
                items = [next(it) for it in iterators]
            except StopIteration:
                return result
            result.append(tuple(items))
