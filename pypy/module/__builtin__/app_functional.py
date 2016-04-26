"""
Plain Python definition of the builtin functions oriented towards
functional programming.
"""
from __future__ import with_statement
import operator
from __pypy__ import resizelist_hint, newlist_hint
from __pypy__ import specialized_zip_2_lists

# ____________________________________________________________

def apply(function, args=(), kwds={}):
    """call a function (or other callable object) and return its result"""
    return function(*args, **kwds)

# ____________________________________________________________

def sorted(iterable, cmp=None, key=None, reverse=False):
    "sorted(iterable, cmp=None, key=None, reverse=False) --> new sorted list"
    sorted_lst = list(iterable)
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


class _Cons(object):
    def __init__(self, prev, iter):
        self.prev = prev
        self.iter = iter

    def fetch(self):
        # recursive, loop-less version of the algorithm: works best for a
        # fixed number of "collections" in the call to map(func, *collections)
        prev = self.prev
        if prev is None:
            args1 = ()
            stop = True
        else:
            args1, stop = prev.fetch()
        iter = self.iter
        if iter is None:
            val = None
        else:
            try:
                val = next(iter)
                stop = False
            except StopIteration:
                self.iter = None
                val = None
        return args1 + (val,), stop

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
        # Special case for the really common case of a single collection
        seq = collections[0]
        with _ManagedNewlistHint(operator._length_hint(seq, 0)) as result:
            for item in seq:
                result.append(func(item))
            return result

    # Gather the iterators into _Cons objects and guess the
    # result length (the max of the input lengths)
    c = None
    max_hint = 0
    for seq in collections:
        c = _Cons(c, iter(seq))
        max_hint = max(max_hint, operator._length_hint(seq, 0))

    with _ManagedNewlistHint(max_hint) as result:
        while True:
            args, stop = c.fetch()
            if stop:
                return result
            if none_func:
                result.append(args)
            else:
                result.append(func(*args))

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
    l = len(sequences)
    if l == 2:
        # A very fast path if the two sequences are lists
        seq0 = sequences[0]
        seq1 = sequences[1]
        try:
            return specialized_zip_2_lists(seq0, seq1)
        except TypeError:
            pass
        # This is functionally the same as the code below, but more
        # efficient because it unrolls the loops over 'sequences'.
        # Only for two arguments, which is the most common case.
        iter0 = iter(seq0)
        iter1 = iter(seq1)
        hint = min(100000000,   # max 100M
                   operator._length_hint(seq0, 0),
                   operator._length_hint(seq1, 0))

        with _ManagedNewlistHint(hint) as result:
            while True:
                try:
                    item0 = next(iter0)
                    item1 = next(iter1)
                except StopIteration:
                    return result
                result.append((item0, item1))

    if l == 0:
        return []

    # Gather the iterators and guess the result length (the min of the
    # input lengths).  If any of the iterators doesn't know its length,
    # we use 0 (instead of ignoring it and using the other iterators;
    # see lib-python's test_builtin.test_zip).
    iterators = []
    hint = 100000000   # max 100M
    for seq in sequences:
        iterators.append(iter(seq))
        hint = min(hint, operator._length_hint(seq, 0))

    with _ManagedNewlistHint(hint) as result:
        while True:
            try:
                items = [next(it) for it in iterators]
            except StopIteration:
                return result
            result.append(tuple(items))
