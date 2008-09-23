"""
Plain Python definition of the builtin functions oriented towards
functional programming.
"""
from __future__ import generators



def sum(sequence, total=0):
    """sum(sequence, start=0) -> value

Returns the sum of a sequence of numbers (NOT strings) plus the value
of parameter 'start'.  When the sequence is empty, returns start."""
    # must forbid "summing" strings, per specs of built-in 'sum'
    if isinstance(total, str): raise TypeError
    for item in sequence:
        total = total + item
    return total

# ____________________________________________________________

def apply(function, args=(), kwds={}):
    """call a function (or other callable object) and return its result"""
    return function(*args, **kwds)

def map(function, *collections):
    """does 3 separate things, hence this enormous docstring.
       1.  if function is None, return a list of tuples, each with one
           item from each collection.  If the collections have different
           lengths,  shorter ones are padded with None.

       2.  if function is not None, and there is only one collection,
           apply function to every item in the collection and return a
           list of the results.

       3.  if function is not None, and there are several collections,
           repeatedly call the function with one argument from each
           collection.  If the collections have different lengths,
           shorter ones are padded with None
    """

    if len(collections) == 0:
        raise TypeError, "map() requires at least one sequence"

    if len(collections) == 1:
        #it's the most common case, so make it faster
        if function is None:
            return list(collections[0])
        return [function(x) for x in collections[0]]

    iterators = [ iter(collection) for collection in collections ]
    res = []
    while 1:
        cont = False     #is any collection not empty?
        args = []
        for iterator in iterators:
            try:
                elem = iterator.next()
                cont = True
            except StopIteration:
                elem = None
            args.append(elem)
        if cont:
            if function is None:
                res.append(tuple(args))
            else:
                res.append(function(*args))
        else:
            return res

def filterstring(function, collection, str_type):
    if function is None and type(collection) is str_type:
        return collection
    res = []
    for i in xrange(len(collection)):
        c = collection[i]
        if function is None or function(c):
            if not isinstance(c, str_type):
                raise TypeError("can't filter %s to %s: __getitem__ returned different type", str_type.__name__, str_type.__name__)
            res.append(c)
    return str_type().join(res)

def filtertuple(function, collection):
    if function is None:
        function = bool
    res = []
    for i in xrange(len(collection)):
        c = collection[i]
        if function(c):
            res.append(c)
    return tuple(res)

def filter(function, collection):
    """construct a list of those elements of collection for which function
       is True.  If function is None, then return the items in the sequence
       which are True."""
    if isinstance(collection, str):
        return filterstring(function, collection, str)
    elif isinstance(collection, unicode):
        return filterstring(function, collection, unicode)
    elif isinstance(collection, tuple):
        return filtertuple(function, collection)

    if function is None:
        return [item for item in collection if item]
    else:
        return [item for item in collection if function(item)]

def zip(*collections):
    """return a list of tuples, where the nth tuple contains every
       nth item of each collection.  If the collections have different
       lengths, zip returns a list as long as the shortest collection,
       ignoring the trailing items in the other collections."""

    if len(collections) == 0:
        import sys
        if sys.version_info < (2,4):
            raise TypeError("zip() requires at least one sequence")
        return []
    res = []
    iterators = [ iter(collection) for collection in collections ]
    while 1:
        try:
            elems = []
            for iterator in iterators:
                elems.append(iterator.next())
            res.append(tuple(elems))
        except StopIteration:
            return res

def reduce(function, seq, *initialt):
    """ Apply function of two arguments cumulatively to the items of
        sequence, from left to right, so as to reduce the sequence to a
        single value.  Optionally begin with an initial value."""

    seqiter = iter(seq)
    if initialt:
       initial, = initialt
    else:
       try:
          initial = seqiter.next()
       except StopIteration:
          raise TypeError, "reduce() of empty sequence with no initial value"
    while 1:
        try:
            arg = seqiter.next()
        except StopIteration:
            break
        initial = function(initial, arg)

    return initial

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


def _identity(arg):
    return arg


def min(*arr, **kwargs):
    """return the smallest number in a list,
    or its smallest argument if more than one is given."""
    from operator import gt

    return min_max(gt, "min", *arr, **kwargs)

def min_max(comp, funcname, *arr, **kwargs):
    key = kwargs.pop("key", _identity)
    if len(kwargs):
        raise TypeError, '%s() got an unexpected keyword argument' % funcname

    if not arr:
        raise TypeError, '%s() takes at least one argument' % funcname

    if len(arr) == 1:
        arr = arr[0]

    iterator = iter(arr)
    try:
        min_max_val = iterator.next()
    except StopIteration:
        raise ValueError, '%s() arg is an empty sequence' % funcname

    keyed_min_max_val = key(min_max_val)

    for i in iterator:
        keyed = key(i)
        if comp(keyed_min_max_val, keyed):
            min_max_val = i
            keyed_min_max_val = keyed
    return min_max_val

def max(*arr, **kwargs):
    """return the largest number in a list,
    or its largest argument if more than one is given."""
    from operator import lt

    return min_max(lt, "max", *arr, **kwargs)

class enumerate(object):
    """enumerate(iterable) -> iterator for (index, value) of iterable.

Return an enumerate object.  iterable must be an other object that supports
iteration.  The enumerate object yields pairs containing a count (from
zero) and a value yielded by the iterable argument.  enumerate is useful
for obtaining an indexed list: (0, seq[0]), (1, seq[1]), (2, seq[2]), ..."""

    def __init__(self, collection):
        self._iter = iter(collection)
        self._index = 0
    
    def next(self):
        try:
            next = self._iter.next
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s object has no next() method' %
                            (type(self._iter).__name__,))
        result = self._index, next()
        self._index += 1
        return result
    
    def __iter__(self):
        return self


# ____________________________________________________________

def sorted(lst, cmp=None, key=None, reverse=None):
    "sorted(iterable, cmp=None, key=None, reverse=False) --> new sorted list"
    sorted_lst = list(lst)
    sorted_lst.sort(cmp, key, reverse)
    return sorted_lst

def reversed(sequence):
    "reversed(sequence) -> reverse iterator over values of the sequence"
    if hasattr(sequence, '__reversed__'):
        return sequence.__reversed__()
    if not hasattr(sequence, '__getitem__'):
        raise TypeError("argument to reversed() must be a sequence")
    return reversed_iterator(sequence)


class reversed_iterator(object):

    def __init__(self, seq):
        self.seq = seq
        self.remaining = len(seq)

    def __iter__(self):
        return self

    def next(self):
        if self.remaining > len(self.seq):
            self.remaining = 0
        i = self.remaining
        if i > 0:
            i -= 1
            item = self.seq[i]
            self.remaining = i
            return item
        raise StopIteration

    def __len__(self):
        if self.remaining > len(self.seq):
            self.remaining = 0
        return self.remaining

    def __reduce__(self):
        tup = (self.seq, self.remaining)
        return (make_reversed_iterator, tup)

def make_reversed_iterator(seq, remaining):
    ri = reversed_iterator.__new__(reversed_iterator)
    ri.seq = seq
    #or "ri = reversed_iterator(seq)" but that executes len(seq)
    ri.remaining = remaining
    return ri

def _install_pickle_support_for_reversed_iterator():
    import _pickle_support
    make_reversed_iterator.__module__ = '_pickle_support'
    _pickle_support.make_reversed_iterator = make_reversed_iterator


