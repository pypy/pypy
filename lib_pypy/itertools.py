# Note that PyPy contains also a built-in module 'itertools' which will
# hide this one if compiled in.

"""Functional tools for creating and using iterators.

Infinite iterators:
count([n]) --> n, n+1, n+2, ...
cycle(p) --> p0, p1, ... plast, p0, p1, ...
repeat(elem [,n]) --> elem, elem, elem, ... endlessly or up to n times

Iterators terminating on the shortest input sequence:
izip(p, q, ...) --> (p[0], q[0]), (p[1], q[1]), ... 
ifilter(pred, seq) --> elements of seq where pred(elem) is True
ifilterfalse(pred, seq) --> elements of seq where pred(elem) is False
islice(seq, [start,] stop [, step]) --> elements from
       seq[start:stop:step]
imap(fun, p, q, ...) --> fun(p0, q0), fun(p1, q1), ...
starmap(fun, seq) --> fun(*seq[0]), fun(*seq[1]), ...
tee(it, n=2) --> (it1, it2 , ... itn) splits one iterator into n
chain(p, q, ...) --> p0, p1, ... plast, q0, q1, ... 
takewhile(pred, seq) --> seq[0], seq[1], until pred fails
dropwhile(pred, seq) --> seq[n], seq[n+1], starting when pred fails
groupby(iterable[, keyfunc]) --> sub-iterators grouped by value of keyfunc(v)
"""

import sys


__all__ = ['chain', 'combinations', 'combinations_with_replacement',
           'compress', 'count', 'cycle', 'dropwhile', 'groupby', 'ifilter',
           'ifilterfalse', 'imap', 'islice', 'izip', 'izip_longest',
           'permutations', 'product', 'repeat', 'starmap', 'takewhile', 'tee']


try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


def _check_number(n):
    if not hasattr(n, '__int__') and not hasattr(n, '__float__'):
        raise TypeError('expected a number')


class chain(object):
    """Make an iterator that returns elements from the first iterable
    until it is exhausted, then proceeds to the next iterable, until
    all of the iterables are exhausted. Used for treating consecutive
    sequences as a single sequence.

    Equivalent to :

    def chain(*iterables):
        for it in iterables:
            for element in it:
                yield element
    """
    def __init__(self, *iterables):
        self._iterables_iter = iter(iterables)
        # little trick for the first chain.next() call
        self._cur_iterable_iter = iter([])

    def __iter__(self):
        return self
    
    def next(self):
        while True:
            try:
                return next(self._cur_iterable_iter)
            except StopIteration:
                self._cur_iterable_iter = iter(next(self._iterables_iter))

    @classmethod
    def from_iterable(cls, iterables):
        c = cls()
        c._iterables_iter = iter(iterables)
        return c


class combinations(object):
    """combinations(iterable, r) --> combinations object

    Return successive r-length combinations of elements in the iterable.

    combinations(range(4), 3) --> (0,1,2), (0,1,3), (0,2,3), (1,2,3)
    """
    def __init__(self, iterable, r):
        self._pool = list(iterable)
        if r < 0:
            raise ValueError('r must be non-negative')
        self._r = r
        self._indices = range(len(self._pool))
        self._last_result = None
        self._stopped = r > len(self._pool)

    def __iter__(self):
        return self

    def _get_maximum(self, i):
        return i + len(self._pool) - self._r

    def _max_index(self, j):
        return self._indices[j - 1] + 1

    def next(self):
        if self._stopped:
            raise StopIteration()
        if self._last_result is None:
            # On the first pass, initialize result tuple using the indices
            result = [None] * self._r
            for i in xrange(self._r):
                index = self._indices[i]
                result[i] = self._pool[index]
        else:
            # Copy the previous result
            result = self._last_result[:]
            # Scan indices right-to-left until finding one that is not at its
            # maximum
            i = self._r - 1
            while i >= 0 and self._indices[i] == self._get_maximum(i):
                i -= 1

            # If i is negative, then the indices are all at their maximum value
            # and we're done
            if i < 0:
                self._stopped = True
                raise StopIteration()

            # Increment the current index which we know is not at its maximum.
            # Then move back to the right setting each index to its lowest
            # possible value
            self._indices[i] += 1
            for j in range(i + 1, self._r):
                self._indices[j] = self._max_index(j)

            # Update the result for the new indices starting with i, the
            # leftmost index that changed
            for i in range(i, self._r):
                index = self._indices[i]
                result[i] = self._pool[index]
        self._last_result = result
        return tuple(result)


class combinations_with_replacement(combinations):
    """combinations_with_replacement(iterable, r) --> combinations_with_replacement object

    Return successive r-length combinations of elements in the iterable
    allowing individual elements to have successive repeats.
    combinations_with_replacement('ABC', 2) --> AA AB AC BB BC CC
    """
    def __init__(self, iterable, r):
        super(combinations_with_replacement, self).__init__(iterable, r)
        self._indices = [0] * r
        self._stopped = len(self._pool) == 0 and r > 0

    def _get_maximum(self, i):
        return len(self._pool) - 1

    def _max_index(self, j):
        return self._indices[j - 1]


class compress(object):
    """Make an iterator that filters elements from data returning
    only those that have a corresponding element in selectors that
    evaluates to True.  Stops when either the data or selectors
    iterables has been exhausted.

    Equivalent to:

    def compress(data, selectors):
        # compress('ABCDEF', [1,0,1,0,1,1]) --> A C E F
        return (d for d, s in izip(data, selectors) if s)
    """
    def __init__(self, data, selectors):
        self._data = iter(data)
        self._selectors = iter(selectors)

    def __iter__(self):
        return self

    def next(self):
        while True:
            next_item = next(self._data)
            next_selector = next(self._selectors)
            if bool(next_selector):
                return next_item


class count(object):
    """Make an iterator that returns evenly spaced values starting
    with n.  If not specified n defaults to zero.  Often used as an
    argument to imap() to generate consecutive data points.  Also,
    used with izip() to add sequence numbers.

    Equivalent to:

    def count(start=0, step=1):
        n = start
        while True:
            yield n
            n += step
    """
    def __init__(self, start=0, step=1):
        _check_number(start)
        _check_number(step)
        self._counter = start
        self._step = step

    def __iter__(self):
        return self

    def next(self):
        c = self._counter
        self._counter += self._step
        return c

    def __reduce__(self):
        if self._step is 1:
            args = (self._counter,)
        else:
            args = (self._counter, self._step)
        return (self.__class__, args)

    def __repr__(self):
        if self._step is 1:
            return 'count(%r)' % (self._counter)
        return 'count(%r, %r)' % (self._counter, self._step)


            
class cycle(object):
    """Make an iterator returning elements from the iterable and
    saving a copy of each. When the iterable is exhausted, return
    elements from the saved copy. Repeats indefinitely.

    Equivalent to :

    def cycle(iterable):
        saved = []
        for element in iterable:
            yield element
            saved.append(element)
        while saved:
            for element in saved:
                yield element    
    """
    def __init__(self, iterable):
        self._cur_iter = self._saving_iter(iter(iterable))
        self._saved = []
        
    def __iter__(self):
        return self

    def _saving_iter(self, iterable):
        while True:
            item = next(iterable)
            self._saved.append(item)
            yield item

    def next(self):
        try:
            item = next(self._cur_iter)
        except StopIteration:
            self._cur_iter = iter(self._saved)
            item = next(self._cur_iter)
        return item
            
        
class dropwhile(object):
    """Make an iterator that drops elements from the iterable as long
    as the predicate is true; afterwards, returns every
    element. Note, the iterator does not produce any output until the
    predicate is true, so it may have a lengthy start-up time.

    Equivalent to :

    def dropwhile(predicate, iterable):
        iterable = iter(iterable)
        for x in iterable:
            if not predicate(x):
                yield x
                break
        for x in iterable:
            yield x
    """
    def __init__(self, predicate, iterable):
        self._predicate = predicate
        self._iter = iter(iterable)
        self._dropped = False

    def __iter__(self):
        return self

    def next(self):
        value = next(self._iter)
        if self._dropped:
            return value
        while self._predicate(value):
            value = next(self._iter)
        self._dropped = True
        return value

class groupby(object):
    """Make an iterator that returns consecutive keys and groups from the
    iterable. The key is a function computing a key value for each
    element. If not specified or is None, key defaults to an identity
    function and returns the element unchanged. Generally, the
    iterable needs to already be sorted on the same key function.

    The returned group is itself an iterator that shares the
    underlying iterable with groupby(). Because the source is shared,
    when the groupby object is advanced, the previous group is no
    longer visible. So, if that data is needed later, it should be
    stored as a list:

       groups = []
       uniquekeys = []
       for k, g in groupby(data, keyfunc):
           groups.append(list(g))      # Store group iterator as a list
           uniquekeys.append(k)
    """    
    def __init__(self, iterable, key=None):
        if key is None:
            key = lambda x: x
        self._keyfunc = key
        self._iter = iter(iterable)
        self._tgtkey = self._currkey = self._currvalue = xrange(0)

    def __iter__(self):
        return self

    def next(self):
        while self._currkey == self._tgtkey:
            self._currvalue = next(self._iter) # Exit on StopIteration
            self._currkey = self._keyfunc(self._currvalue)
        self._tgtkey = self._currkey
        return (self._currkey, self._grouper(self._tgtkey))

    def _grouper(self, tgtkey):
        while self._currkey == tgtkey:
            yield self._currvalue
            self._currvalue = next(self._iter) # Exit on StopIteration
            self._currkey = self._keyfunc(self._currvalue)



class _ifilter_base(object):
    """base class for ifilter and ifilterflase"""
    def __init__(self, predicate, iterable):
        # Make sure iterable *IS* iterable
        self._iter = iter(iterable)
        if predicate is None:
            self._predicate = bool
        else:
            self._predicate = predicate

    def __iter__(self):
        return self
    
class ifilter(_ifilter_base):
    """Make an iterator that filters elements from iterable returning
    only those for which the predicate is True.  If predicate is
    None, return the items that are true.

    Equivalent to :

    def ifilter:
        if predicate is None:
            predicate = bool
        for x in iterable:
            if predicate(x):
                yield x
    """
    def next(self):
        while True:
            next_elt = next(self._iter)
            if self._predicate(next_elt):
                return next_elt

class ifilterfalse(_ifilter_base):
    """Make an iterator that filters elements from iterable returning
    only those for which the predicate is False.  If predicate is
    None, return the items that are false.

    Equivalent to :
    
    def ifilterfalse(predicate, iterable):
        if predicate is None:
            predicate = bool
        for x in iterable:
            if not predicate(x):
                yield x
    """
    def next(self):
        while True:
            next_elt = next(self._iter)
            if not self._predicate(next_elt):
                return next_elt
             



class imap(object):
    """Make an iterator that computes the function using arguments
    from each of the iterables. If function is set to None, then
    imap() returns the arguments as a tuple. Like map() but stops
    when the shortest iterable is exhausted instead of filling in
    None for shorter iterables. The reason for the difference is that
    infinite iterator arguments are typically an error for map()
    (because the output is fully evaluated) but represent a common
    and useful way of supplying arguments to imap().

    Equivalent to :

    def imap(function, *iterables):
        iterables = map(iter, iterables)
        while True:
            args = [i.next() for i in iterables]
            if function is None:
                yield tuple(args)
            else:
                yield function(*args)
    
    """
    def __init__(self, function, iterable, *other_iterables):
        if function is None:
            function = lambda *args: args
        self._func = function
        self._iters = map(iter, (iterable, ) + other_iterables)

    def __iter__(self):
        return self

    def next(self):
        args = [next(it) for it in self._iters]
        return self._func(*args)



class islice(object):
    """Make an iterator that returns selected elements from the
    iterable.  If start is non-zero, then elements from the iterable
    are skipped until start is reached. Afterward, elements are
    returned consecutively unless step is set higher than one which
    results in items being skipped. If stop is None, then iteration
    continues until the iterator is exhausted, if at all; otherwise,
    it stops at the specified position. Unlike regular slicing,
    islice() does not support negative values for start, stop, or
    step. Can be used to extract related fields from data where the
    internal structure has been flattened (for example, a multi-line
    report may list a name field on every third line).
    """ 
    def __init__(self, iterable, *args):
        s = slice(*args)
        for n, v in zip(['Start', 'Stop', 'Step'], [s.start, s.stop, s.step]):
            if not (v is None or isinstance(v, int) and 0 <= v):
                msg = ('%s for islice must be None or an integer: '
                       '0 <= x <= maxint')
                raise ValueError(msg % n)
        start, stop, self._step = s.indices(sys.maxint)
        self._iter = iter(iterable)
        self._pos = -1
        self._next_pos = start
        self._max_pos = stop - 1

    def __iter__(self):
        return self

    def next(self):
        i = self._pos
        while i < self._next_pos:
            if i >= self._max_pos:
                raise StopIteration()
            item = next(self._iter)
            i += 1

        self._pos = i
        self._next_pos += self._step
        return item

class izip(object):
    """Make an iterator that aggregates elements from each of the
    iterables.  Like zip() except that it returns an iterator instead
    of a list. Used for lock-step iteration over several iterables at
    a time.

    Equivalent to :

    def izip(*iterables):
        iterables = map(iter, iterables)
        while iterables:
            result = [i.next() for i in iterables]
            yield tuple(result)
    """
    def __init__(self, *iterables):
        self._iterators = map(iter, iterables)

    def __iter__(self):
        return self

    def next(self):
        if not self._iterators:
            raise StopIteration()
        return tuple([next(i) for i in self._iterators])


class izip_longest(object):
    """Return an izip_longest object whose .next() method returns a tuple where
    the i-th element comes from the i-th iterable argument.  The .next()
    method continues until the longest iterable in the argument sequence
    is exhausted and then it raises StopIteration.  When the shorter iterables
    are exhausted, the fillvalue is substituted in their place.  The fillvalue
    defaults to None or can be specified by a keyword argument.
    """
    def __init__(self, *iterables, **kwargs):
        self._fillvalue = kwargs.pop('fillvalue', None)
        if kwargs:
            msg = 'izip_longest() got unexpected keyword argument(s)'
            raise TypeError(msg)
        self._iters = map(iter, iterables)
        self._iters_yielding = len(self._iters)

    def __iter__(self):
        return self

    def next(self):
        if self._iters_yielding <= 0:
            raise StopIteration()
        result = [None] * len(self._iters)
        for i, iterator in enumerate(self._iters):
            try:
                item = next(iterator)
            except StopIteration:
                self._iters_yielding -= 1
                if self._iters_yielding <= 0:
                    raise
                self._iters[i] = repeat(self._fillvalue)
                item = self._fillvalue
            result[i] = item
        return tuple(result)


class permutations(object):
    """permutations(iterable[, r]) --> permutations object

    Return successive r-length permutations of elements in the iterable.

    permutations(range(3), 2) --> (0,1), (0,2), (1,0), (1,2), (2,0), (2,1)
    """
    def __init__(self, iterable, r=None):
        self._pool = list(iterable)
        n = len(self._pool)
        if r is None:
            r = n
        elif r < 0:
            raise ValueError('r must be non-negative')
        self._r = r
        self._indices = range(n)
        self._cycles = range(n, n - r, -1)
        self._stopped = r > n

    def __iter__(self):
        return self

    def next(self):
        if self._stopped:
            raise StopIteration()

        r = self._r
        indices = self._indices
        cycles = self._cycles

        result = tuple([self._pool[indices[i]] for i in range(r)])
        i = r - 1
        while i >= 0:
            j = cycles[i] - 1
            if j > 0:
                cycles[i] = j
                indices[i], indices[-j] = indices[-j], indices[i]
                return result
            cycles[i] = len(indices) - i
            n1 = len(indices) - 1
            assert n1 >= 0
            num = indices[i]
            for k in range(i, n1):
                indices[k] = indices[k+1]
            indices[n1] = num
            i -= 1
        self._stopped = True
        return result


class product(object):
    """Cartesian product of input iterables.

    Equivalent to nested for-loops in a generator expression. For example,
    ``product(A, B)`` returns the same as ``((x,y) for x in A for y in B)``.

    The nested loops cycle like an odometer with the rightmost element advancing
    on every iteration.  This pattern creates a lexicographic ordering so that if
    the input's iterables are sorted, the product tuples are emitted in sorted
    order.

    To compute the product of an iterable with itself, specify the number of
    repetitions with the optional *repeat* keyword argument.  For example,
    ``product(A, repeat=4)`` means the same as ``product(A, A, A, A)``.

    This function is equivalent to the following code, except that the
    actual implementation does not build up intermediate results in memory::

        def product(*args, **kwds):
            # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
            # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
            pools = map(tuple, args) * kwds.get('repeat', 1)
            result = [[]]
            for pool in pools:
                result = [x+[y] for x in result for y in pool]
            for prod in result:
                yield tuple(prod)
    """
    def __init__(self, *args, **kw):
        repeat = kw.pop('repeat', 1)
        if kw:
            msg = 'product() got unexpected keyword argument(s)'
            raise TypeError(msg)
        self._pools = map(tuple, args) * repeat
        self._indices = [0] * len(self._pools)
        try:
            self._next_result = [s[0] for s in self._pools]
        except IndexError:
            self._next_result = None

    def __iter__(self):
        return self

    def next(self):
        pools = self._pools
        indices = self._indices

        if self._next_result is None:
            raise StopIteration()

        result = tuple(self._next_result)

        i = len(pools)
        while True:
            i -= 1
            if i < 0:
                self._next_result = None
                return result
            j = indices[i]
            j += 1
            if j < len(pools[i]):
                break

        self._next_result[i] = pools[i][j]
        indices[i] = j

        while True:
            i += 1
            if i >= len(pools):
                break
            indices[i] = 0
            self._next_result[i] = pools[i][0]

        return result


class repeat(object):
    """Make an iterator that returns object over and over again.
    Runs indefinitely unless the times argument is specified.  Used
    as argument to imap() for invariant parameters to the called
    function. Also used with izip() to create an invariant part of a
    tuple record.

    Equivalent to :

    def repeat(object, times=None):
        if times is None:
            while True:
                yield object
        else:
            for i in xrange(times):
                yield object
    """
    def __init__(self, object, times=None):
        self._obj = object
        if times is not None:
            xrange(times) # Raise a TypeError
            if times < 0:
                times = 0
        self._times = times
        
    def __iter__(self):
        return self

    def next(self):
        # next() *need* to decrement self._times when consumed
        if self._times is not None:
            if self._times <= 0: 
                raise StopIteration()
            self._times -= 1
        return self._obj

    def __repr__(self):
        if self._times is not None:
            return 'repeat(%r, %r)' % (self._obj, self._times)
        else:
            return 'repeat(%r)' % (self._obj,)

    def __len__(self):
        if self._times == -1 or self._times is None:
            raise TypeError("len() of unsized object")
        return self._times
    

class starmap(object):
    """Make an iterator that computes the function using arguments
    tuples obtained from the iterable. Used instead of imap() when
    argument parameters are already grouped in tuples from a single
    iterable (the data has been ``pre-zipped''). The difference
    between imap() and starmap() parallels the distinction between
    function(a,b) and function(*c).

    Equivalent to :

    def starmap(function, iterable):
        iterable = iter(iterable)
        while True:
            yield function(*iterable.next())    
    """
    def __init__(self, function, iterable):
        self._func = function
        self._iter = iter(iterable)

    def __iter__(self):
        return self

    def next(self):
        t = next(self._iter)
        return self._func(*t)



class takewhile(object):
    """Make an iterator that returns elements from the iterable as
    long as the predicate is true.

    Equivalent to :
    
    def takewhile(predicate, iterable):
        for x in iterable:
            if predicate(x):
                yield x
            else:
                break
    """
    def __init__(self, predicate, iterable):
        self._predicate = predicate
        self._iter = iter(iterable)

    def __iter__(self):
        return self

    def next(self):
        value = next(self._iter)
        if not self._predicate(value):
            self._iter = iter([])
            raise StopIteration()
        return value

    
class _TeeData(object):
    """Holds cached values for TeeObjects"""
    def __init__(self, iterator):
        self.data = []
        self._iter = iterator

    def __getitem__(self, i):
        # iterates until 'i' if not done yet
        while i >= len(self.data):
            value = next(self._iter)
            self.data.append(value)
        return self.data[i]


class _TeeObject(object):
    """Iterables / Iterators as returned by the tee() function"""
    def __init__(self, iterable=None, tee_data=None):
        if tee_data:
            self.tee_data = tee_data
            self.pos = 0
        # <=> Copy constructor
        elif isinstance(iterable, _TeeObject):
            self.tee_data = iterable.tee_data
            self.pos = iterable.pos
        else:
            self.tee_data = _TeeData(iter(iterable))
            self.pos = 0
            
    def next(self):
        data = self.tee_data[self.pos]
        self.pos += 1
        return data
    
    def __iter__(self):
        return self


@builtinify
def tee(iterable, n=2):
    """Return n independent iterators from a single iterable.
    Note : once tee() has made a split, the original iterable
    should not be used anywhere else; otherwise, the iterable could get
    advanced without the tee objects being informed.
    
    Note : this member of the toolkit may require significant auxiliary
    storage (depending on how much temporary data needs to be stored).
    In general, if one iterator is going to use most or all of the
    data before the other iterator, it is faster to use list() instead
    of tee()
    
    Equivalent to :
    
    def tee(iterable, n=2):
        def gen(next, data={}, cnt=[0]):
            for i in count():
                if i == cnt[0]:
                    item = data[i] = next()
                    cnt[0] += 1
                else:
                    item = data.pop(i)
                yield item
        it = iter(iterable)
        return tuple([gen(it.next) for i in range(n)])
    """
    if n < 0:
        raise ValueError('n must be >= 0')
    if isinstance(iterable, _TeeObject):
        # a,b = tee(range(10)) ; c,d = tee(a) ; self.assert_(a is c)
        return tuple([iterable] + [_TeeObject(iterable) for i in xrange(n-1)])
    tee_data = _TeeData(iter(iterable))
    return tuple([_TeeObject(tee_data=tee_data) for i in xrange(n)])
