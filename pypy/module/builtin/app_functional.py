"""
Plain Python definition of the builtin functions oriented towards
functional programming.
"""
from __future__ import generators

def sum(sequence, total=0):
    # must forbid "summing" strings, per specs of built-in 'sum'
    if isinstance(total, str): raise TypeError
    for item in sequence:
        total = total + item
    return total

# ____________________________________________________________

def apply(function, args, kwds={}):
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

def filter(function, collection):
    """construct a list of those elements of collection for which function
       is True.  If function is None, then return the items in the sequence
       which are True."""
    str_type = None
    if isinstance(collection, str):
        str_type = str
    elif isinstance(collection, unicode):
        str_type = unicode

    if str_type is not None:
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
        
    if function is None:
        res = [item for item in collection if item]
    else:
        res = [item for item in collection if function(item)]

    if isinstance(collection, tuple):
       return tuple(res)
    else:
       return res

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
        raise TypeError('range() interger start argument expected, got %s' % type(start))
    if not isinstance(stop, (int, long)):
        raise TypeError('range() interger stop argument expected, got %s' % type(stop))
    if not isinstance(step, (int, long)):
        raise TypeError('range() interger step argument expected, got %s' % type(step))

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

# min and max could be one function if we had operator.__gt__ and
# operator.__lt__  Perhaps later when we have operator.

def min(*arr):
    """return the smallest number in a list"""

    if not arr:
        raise TypeError, 'min() takes at least one argument'

    if len(arr) == 1:
        arr = arr[0]

    iterator = iter(arr)
    try:
        min = iterator.next()
    except StopIteration:
        raise ValueError, 'min() arg is an empty sequence'

    for i in iterator:
        if min > i:
            min = i
    return min

def max(*arr):
    """return the largest number in a list"""

    if not arr:
        raise TypeError, 'max() takes at least one argument'

    if len(arr) == 1:
        arr = arr[0]

    iterator = iter(arr)
    try:
        max = iterator.next()
    except StopIteration:
        raise ValueError, 'max() arg is an empty sequence'

    for i in iterator:
        if max < i:
            max = i
    return max

def enumerate(collection):
    'Generates an indexed series:  (0,coll[0]), (1,coll[1]) ...'
    it = iter(collection)   # raises a TypeError early
    def do_enumerate(it):
        index = 0
        for value in it:
            yield index, value
            index += 1
    return do_enumerate(it)

# ____________________________________________________________

class xrange(object):
    def __init__(self, start, stop=None, step=1):
        if not isinstance(start, (int, long, float)):
            raise TypeError('an integer is required')
        start = int(start)
        if stop is None:
            self.start = 0
            self.stop = start
        else:
            if not isinstance(stop, (int, long, float)):
                raise TypeError('an integer is required')
            stop = int(stop)
            self.start = start
            self.stop = stop
        if not isinstance(step, (int, long, float)):
            raise TypeError('an integer is required')
        step = int(step)
        if step == 0:
            raise ValueError, 'xrange() step-argument (arg 3) must not be zero'
        self.step = step

    def __len__(self):
        if not hasattr(self, '_len'):
            slicelength = self.stop - self.start
            lengthsign = cmp(slicelength, 0)
            stepsign = cmp(self.step, 0)
            if stepsign == lengthsign:
                self._len = (slicelength - lengthsign) // self.step + 1
            else:
                self._len = 0
        return self._len

    def __getitem__(self, index):
        # xrange does NOT support slicing
        if not isinstance(index, int):
            raise TypeError, "sequence index must be integer"
        len = self.__len__()
        if index<0:
            index += len
        if 0 <= index < len:
            return self.start + index * self.step
        raise IndexError, "xrange object index out of range"

    def __iter__(self):
        start, stop, step = self.start, self.stop, self.step
        i = start
        if step > 0:
            while i < stop:
                yield i
                i+=step
        else:
            while i > stop:
                yield i
                i+=step

# ____________________________________________________________

def sorted(lst, cmp=None, key=None, reverse=None):
    "sorted(iterable, cmp=None, key=None, reverse=False) --> new sorted list"
    sorted_lst = list(lst)
    sorted_lst.sort(cmp, key, reverse)
    return sorted_lst

def reversed(iterable):
    """reversed(sequence) -> reverse iterator over values of the sequence

    Return a reverse iterator
    """
    if hasattr(iterable, '__reversed__'):
        return iterable.__reversed__()
    seq = list(iterable)
    def reversed_gen(local_iterable):
        len_iterable = len(local_iterable)
        for index in range(len_iterable-1, -1, -1):
            yield local_iterable[index]
    return reversed_gen(seq)
