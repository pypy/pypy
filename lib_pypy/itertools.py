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

__all__ = ['chain', 'count', 'cycle', 'dropwhile', 'groupby', 'ifilter',
           'ifilterfalse', 'imap', 'islice', 'izip', 'repeat', 'starmap',
           'takewhile', 'tee']


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
        self._iterables_iter = iter(map(iter, iterables))
        # little trick for the first chain.next() call
        self._cur_iterable_iter = iter([])

    def __iter__(self):
        return self
    
    def next(self):
        while True:
            try:
                return self._cur_iterable_iter.next()
            except StopIteration:
                self._cur_iterable_iter = self._iterables_iter.next()
            except AttributeError:
                # CPython raises a TypeError when next() is not defined
                raise TypeError('%s has no next() method' % \
                                (self._cur_iterable_iter))

class count(object):
    """Make an iterator that returns consecutive integers starting
    with n.  If not specified n defaults to zero. Does not currently
    support python long integers. Often used as an argument to imap()
    to generate consecutive data points.  Also, used with izip() to
    add sequence numbers.

    Equivalent to :

    def count(n=0):
        if not isinstance(n, int):
            raise TypeError("%s is not a regular integer" % n)
        while True:
            yield n
            n += 1
    """
    def __init__(self, n=0):
        if not isinstance(n, int):
            raise TypeError('%s is not a regular integer' % n)
        self.times = n-1

    def __iter__(self):
        return self

    def next(self):
        self.times += 1
        return self.times

    def __repr__(self):
        return 'count(%d)' % (self.times + 1)


            
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
        self._cur_iter = iter(iterable)
        self._saved = []
        self._must_save = True
        
    def __iter__(self):
        return self

    def next(self):
        # XXX Could probably be improved
        try:
            next_elt = self._cur_iter.next()
            if self._must_save:
                self._saved.append(next_elt)
        except StopIteration:
            self._cur_iter = iter(self._saved)
            next_elt = self._cur_iter.next()
            self._must_save = False
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % \
                            (self._cur_iter))
        return next_elt
            
        
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
        try:
            value = self._iter.next()
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % \
                            (self._iter))
        if self._dropped:
            return value
        while self._predicate(value):
            value = self._iter.next()
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
        self.keyfunc = key
        self.it = iter(iterable)
        self.tgtkey = self.currkey = self.currvalue = xrange(0)

    def __iter__(self):
        return self

    def next(self):
        while self.currkey == self.tgtkey:
            try:
                self.currvalue = self.it.next() # Exit on StopIteration
            except AttributeError:
                # CPython raises a TypeError when next() is not defined
                raise TypeError('%s has no next() method' % \
                                (self.it))            
            self.currkey = self.keyfunc(self.currvalue)
        self.tgtkey = self.currkey
        return (self.currkey, self._grouper(self.tgtkey))

    def _grouper(self, tgtkey):
        while self.currkey == tgtkey:
            yield self.currvalue
            self.currvalue = self.it.next() # Exit on StopIteration
            self.currkey = self.keyfunc(self.currvalue)



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
        try:
            next_elt = self._iter.next()
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % \
                            (self._iter))
        while True:
            if self._predicate(next_elt):
                return next_elt
            next_elt = self._iter.next()

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
        try:
            next_elt = self._iter.next()
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % \
                            (self._iter))
        while True:
            if not self._predicate(next_elt):
                return next_elt
            next_elt = self._iter.next()
             



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
        self._func = function
        self._iters = map(iter, (iterable, ) + other_iterables)

    def __iter__(self):
        return self

    def next(self):
        try:
            args = [it.next() for it in self._iters]
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % \
                            (it))
        if self._func is None:
            return tuple(args)
        else:
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
        self.start, self.stop, self.step = s.start or 0, s.stop, s.step
        if not isinstance(self.start, (int, long)):
           raise ValueError("Start argument must be an integer")
        if self.stop is not None and not isinstance(self.stop, (int,long)):
           raise ValueError("Stop argument must be an integer or None")
        if self.step is None:
            self.step = 1
        if self.start<0 or (self.stop is not None and self.stop<0
           ) or self.step<=0:
            raise ValueError, "indices for islice() must be positive"
        self.it = iter(iterable)
        self.donext = None
        self.cnt = 0

    def __iter__(self):
        return self

    def next(self): 
        if self.donext is None:
            try:
                self.donext = self.it.next
            except AttributeError:
                raise TypeError
        nextindex = self.start
        if self.stop is not None and nextindex >= self.stop:
            raise StopIteration
        while self.cnt <= nextindex:
            nextitem = self.donext()
            self.cnt += 1
        self.start += self.step 
        return nextitem

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
        self._result = [None] * len(self._iterators)

    def __iter__(self):
        return self

    def next(self):
        if not self._iterators:
            raise StopIteration()
        try:
            return tuple([i.next() for i in self._iterators])
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % (i))
    

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
    def __init__(self, obj, times=None):
        self._obj = obj
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
            raise TypeError("len() of uniszed object")
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
        # CPython raises a TypeError when the iterator doesn't return a tuple
        try:
            t = self._iter.next()
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % self._iter)
        if not isinstance(t, tuple):
            raise TypeError("iterator must return a tuple")
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
        try:
            value = self._iter.next()
        except AttributeError:
            # CPython raises a TypeError when next() is not defined
            raise TypeError('%s has no next() method' % \
                            (self._iter))
        if not self._predicate(value):
            raise StopIteration()
        return value

    
class TeeData(object):
    """Holds cached values for TeeObjects"""
    def __init__(self, iterator):
        self.data = []
        self._iter = iterator

    def __getitem__(self, i):
        # iterates until 'i' if not done yet
        while i>= len(self.data):
            try:
                self.data.append( self._iter.next() )
            except AttributeError:
                # CPython raises a TypeError when next() is not defined
                raise TypeError('%s has no next() method' % self._iter)
        return self.data[i]


class TeeObject(object):
    """Iterables / Iterators as returned by the tee() function"""
    def __init__(self, iterable=None, tee_data=None):
        if tee_data:
            self.tee_data = tee_data
            self.pos = 0
        # <=> Copy constructor
        elif isinstance(iterable, TeeObject):
            self.tee_data = iterable.tee_data
            self.pos = iterable.pos
        else:
            self.tee_data = TeeData(iter(iterable))
            self.pos = 0
            
    def next(self):
        data = self.tee_data[self.pos]
        self.pos += 1
        return data
    
    def __iter__(self):
        return self

    
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
    if isinstance(iterable, TeeObject):
        # a,b = tee(range(10)) ; c,d = tee(a) ; self.assert_(a is c)
        return tuple([iterable] +
        [TeeObject(tee_data=iterable.tee_data) for i in xrange(n-1)])
    tee_data = TeeData(iter(iterable))
    return tuple([TeeObject(tee_data=tee_data) for i in xrange(n)])
