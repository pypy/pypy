from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.gateway import interp2app, unwrap_spec

class W_Count(Wrappable):

    def __init__(self, space, w_firstval, w_step):
        self.space = space
        self.w_c = w_firstval
        self.w_step = w_step

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        w_c = self.w_c
        self.w_c = self.space.add(w_c, self.w_step)
        return w_c

    def single_argument(self):
        space = self.space
        return (space.isinstance_w(self.w_step, space.w_int) and
                space.eq_w(self.w_step, space.wrap(1)))

    def repr_w(self):
        space = self.space
        c = space.str_w(space.repr(self.w_c))
        if self.single_argument():
            s = 'count(%s)' % (c,)
        else:
            step = space.str_w(space.repr(self.w_step))
            s = 'count(%s, %s)' % (c, step)
        return self.space.wrap(s)

    def reduce_w(self):
        space = self.space
        if self.single_argument():
            args_w = [self.w_c]
        else:
            args_w = [self.w_c, self.w_step]
        return space.newtuple([space.gettypefor(W_Count),
                               space.newtuple(args_w)])

def check_number(space, w_obj):
    if (space.lookup(w_obj, '__add__') is None or
        space.is_true(space.isinstance(w_obj, space.w_str)) or
        space.is_true(space.isinstance(w_obj, space.w_unicode))):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected a number"))

def W_Count___new__(space, w_subtype, w_start=0, w_step=1):
    check_number(space, w_start)
    check_number(space, w_step)
    r = space.allocate_instance(W_Count, w_subtype)
    r.__init__(space, w_start, w_step)
    return space.wrap(r)

W_Count.typedef = TypeDef(
        'count',
        __module__ = 'itertools',
        __new__ = interp2app(W_Count___new__),
        __iter__ = interp2app(W_Count.iter_w),
        next = interp2app(W_Count.next_w),
        __reduce__ = interp2app(W_Count.reduce_w),
        __repr__ = interp2app(W_Count.repr_w),
        __doc__ = """Make an iterator that returns consecutive integers starting
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
    """)


class W_Repeat(Wrappable):

    def __init__(self, space, w_obj, w_times):
        self.space = space
        self.w_obj = w_obj

        if space.is_w(w_times, space.w_None):
            self.counting = False
            self.count = 0
        else:
            self.counting = True
            self.count = self.space.int_w(w_times)

    def next_w(self):
        if self.counting:
            if self.count <= 0:
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            self.count -= 1
        return self.w_obj

    def iter_w(self):
        return self.space.wrap(self)

    def repr_w(self):
        objrepr = self.space.str_w(self.space.repr(self.w_obj))
        if self.counting:
            s = 'repeat(%s, %d)' % (objrepr, self.count)
        else:
            s = 'repeat(%s)' % (objrepr,)
        return self.space.wrap(s)

def W_Repeat___new__(space, w_subtype, w_object, w_times=None):
    r = space.allocate_instance(W_Repeat, w_subtype)
    r.__init__(space, w_object, w_times)
    return space.wrap(r)

W_Repeat.typedef = TypeDef(
        'repeat',
        __module__ = 'itertools',
        __new__  = interp2app(W_Repeat___new__),
        __iter__ = interp2app(W_Repeat.iter_w),
        next     = interp2app(W_Repeat.next_w),
        __repr__ = interp2app(W_Repeat.repr_w),
        __doc__  = """Make an iterator that returns object over and over again.
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
    """)

class W_TakeWhile(Wrappable):

    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)
        self.stopped = False

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.stopped:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        w_obj = self.space.next(self.iterable)  # may raise a w_StopIteration
        w_bool = self.space.call_function(self.w_predicate, w_obj)
        if not self.space.is_true(w_bool):
            self.stopped = True
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        return w_obj

def W_TakeWhile___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_TakeWhile, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return space.wrap(r)


W_TakeWhile.typedef = TypeDef(
        'takewhile',
        __module__ = 'itertools',
        __new__  = interp2app(W_TakeWhile___new__),
        __iter__ = interp2app(W_TakeWhile.iter_w),
        next     = interp2app(W_TakeWhile.next_w),
        __doc__  = """Make an iterator that returns elements from the iterable as
    long as the predicate is true.

    Equivalent to :

    def takewhile(predicate, iterable):
        for x in iterable:
            if predicate(x):
                yield x
            else:
                break
    """)

class W_DropWhile(Wrappable):

    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)
        self.started = False

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.started:
            w_obj = self.space.next(self.iterable)  # may raise w_StopIteration
        else:
            while True:
                w_obj = self.space.next(self.iterable)  # may raise w_StopIter
                w_bool = self.space.call_function(self.w_predicate, w_obj)
                if not self.space.is_true(w_bool):
                    self.started = True
                    break

        return w_obj

def W_DropWhile___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_DropWhile, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return space.wrap(r)


W_DropWhile.typedef = TypeDef(
        'dropwhile',
        __module__ = 'itertools',
        __new__  = interp2app(W_DropWhile___new__),
        __iter__ = interp2app(W_DropWhile.iter_w),
        next     = interp2app(W_DropWhile.next_w),
        __doc__  = """Make an iterator that drops elements from the iterable as long
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
    """)

class _IFilterBase(Wrappable):

    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        if space.is_w(w_predicate, space.w_None):
            self.no_predicate = True
        else:
            self.no_predicate = False
            self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        while True:
            w_obj = self.space.next(self.iterable)  # may raise w_StopIteration
            if self.no_predicate:
                pred = self.space.is_true(w_obj)
            else:
                w_pred = self.space.call_function(self.w_predicate, w_obj)
                pred = self.space.is_true(w_pred)
            if pred ^ self.reverse:
                return w_obj


class W_IFilter(_IFilterBase):
    reverse = False

def W_IFilter___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_IFilter, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return space.wrap(r)

W_IFilter.typedef = TypeDef(
        'ifilter',
        __module__ = 'itertools',
        __new__  = interp2app(W_IFilter___new__),
        __iter__ = interp2app(W_IFilter.iter_w),
        next     = interp2app(W_IFilter.next_w),
        __doc__  = """Make an iterator that filters elements from iterable returning
    only those for which the predicate is True.  If predicate is
    None, return the items that are true.

    Equivalent to :

    def ifilter:
        if predicate is None:
            predicate = bool
        for x in iterable:
            if predicate(x):
                yield x
    """)

class W_IFilterFalse(_IFilterBase):
    reverse = True

def W_IFilterFalse___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_IFilterFalse, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return space.wrap(r)

W_IFilterFalse.typedef = TypeDef(
        'ifilterfalse',
        __module__ = 'itertools',
        __new__  = interp2app(W_IFilterFalse___new__),
        __iter__ = interp2app(W_IFilterFalse.iter_w),
        next     = interp2app(W_IFilterFalse.next_w),
        __doc__  = """Make an iterator that filters elements from iterable returning
    only those for which the predicate is False.  If predicate is
    None, return the items that are false.

    Equivalent to :

    def ifilterfalse(predicate, iterable):
        if predicate is None:
            predicate = bool
        for x in iterable:
            if not predicate(x):
                yield x
    """)

class W_ISlice(Wrappable):
    def __init__(self, space, w_iterable, w_startstop, args_w):
        self.iterable = space.iter(w_iterable)
        self.space = space

        num_args = len(args_w)

        if num_args == 0:
            start = 0
            w_stop = w_startstop
        elif num_args <= 2:
            if space.is_w(w_startstop, space.w_None):
                start = 0
            else:
                start = space.int_w(w_startstop)
            w_stop = args_w[0]
        else:
            raise OperationError(space.w_TypeError, space.wrap("islice() takes at most 4 arguments (" + str(num_args) + " given)"))

        if space.is_w(w_stop, space.w_None):
            stop = -1
            stoppable = False
        else:
            stop = space.int_w(w_stop)
            stoppable = True

        if num_args == 2:
            w_step = args_w[1]
            if space.is_w(w_step, space.w_None):
                step = 1
            else:
                step = space.int_w(w_step)
        else:
            step = 1

        if start < 0:
            raise OperationError(space.w_ValueError, space.wrap("Indicies for islice() must be non-negative integers."))
        if stoppable and stop < 0:
            raise OperationError(space.w_ValueError, space.wrap("Stop argument must be a non-negative integer or None."))
        if step < 1:
            raise OperationError(space.w_ValueError, space.wrap("Step must be one or lager for islice()."))

        self.start = start
        self.stop = stop
        self.step = step

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.start >= 0:               # first call only
            consume = self.start + 1
            self.start = -1
        else:                             # all following calls
            consume = self.step
        if self.stop >= 0:
            if self.stop < consume:
                raise OperationError(self.space.w_StopIteration,
                                     self.space.w_None)
            self.stop -= consume
        while True:
            w_obj = self.space.next(self.iterable)
            consume -= 1
            if consume <= 0:
                return w_obj

def W_ISlice___new__(space, w_subtype, w_iterable, w_startstop, args_w):
    r = space.allocate_instance(W_ISlice, w_subtype)
    r.__init__(space, w_iterable, w_startstop, args_w)
    return space.wrap(r)

W_ISlice.typedef = TypeDef(
        'islice',
        __module__ = 'itertools',
        __new__  = interp2app(W_ISlice___new__),
        __iter__ = interp2app(W_ISlice.iter_w),
        next     = interp2app(W_ISlice.next_w),
        __doc__  = """Make an iterator that returns selected elements from the
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
    """)


class W_Chain(Wrappable):
    def __init__(self, space, w_iterables):
        self.space = space
        self.w_iterables = w_iterables
        self.w_it = None

    def iter_w(self):
        return self.space.wrap(self)

    def _advance(self):
        self.w_it = self.space.iter(self.space.next(self.w_iterables))

    def next_w(self):
        if not self.w_iterables:
            # already stopped
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        if not self.w_it:
            self._advance()
        try:
            return self.space.next(self.w_it)
        except OperationError, e:
            return self._handle_error(e)

    def _handle_error(self, e):
        while True:
            if not e.match(self.space, self.space.w_StopIteration):
                raise e
            self._advance() # may raise StopIteration itself
            try:
                return self.space.next(self.w_it)
            except OperationError, e:
                pass # loop back to the start of _handle_error(e)

def W_Chain___new__(space, w_subtype, args_w):
    r = space.allocate_instance(W_Chain, w_subtype)
    w_args = space.newtuple(args_w)
    r.__init__(space, space.iter(w_args))
    return space.wrap(r)

def chain_from_iterable(space, w_cls, w_arg):
    """chain.from_iterable(iterable) --> chain object

    Alternate chain() contructor taking a single iterable argument
    that evaluates lazily."""
    r = space.allocate_instance(W_Chain, w_cls)
    r.__init__(space, space.iter(w_arg))
    return space.wrap(r)

W_Chain.typedef = TypeDef(
        'chain',
        __module__ = 'itertools',
        __new__  = interp2app(W_Chain___new__),
        __iter__ = interp2app(W_Chain.iter_w),
        next     = interp2app(W_Chain.next_w),
        from_iterable = interp2app(chain_from_iterable, as_classmethod=True),
        __doc__  = """Make an iterator that returns elements from the first iterable
    until it is exhausted, then proceeds to the next iterable, until
    all of the iterables are exhausted. Used for treating consecutive
    sequences as a single sequence.

    Equivalent to :

    def chain(*iterables):
        for it in iterables:
            for element in it:
                yield element
    """)

class W_IMap(Wrappable):
    _error_name = "imap"
    _immutable_fields_ = ["w_fun", "iterators_w"]

    def __init__(self, space, w_fun, args_w):
        self.space = space
        if self.space.is_w(w_fun, space.w_None):
            self.w_fun = None
        else:
            self.w_fun = w_fun

        iterators_w = []
        i = 0
        for iterable_w in args_w:
            try:
                iterator_w = space.iter(iterable_w)
            except OperationError, e:
                if e.match(self.space, self.space.w_TypeError):
                    raise OperationError(space.w_TypeError, space.wrap(self._error_name + " argument #" + str(i + 1) + " must support iteration"))
                else:
                    raise
            else:
                iterators_w.append(iterator_w)

            i += 1

        self.iterators_w = iterators_w

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        # common case: 1 or 2 arguments
        iterators_w = self.iterators_w
        length = len(iterators_w)
        if length == 1:
            objects = [self.space.next(iterators_w[0])]
        elif length == 2:
            objects = [self.space.next(iterators_w[0]),
                       self.space.next(iterators_w[1])]
        else:
            objects = self._get_objects()
        w_objects = self.space.newtuple(objects)
        if self.w_fun is None:
            return w_objects
        else:
            return self.space.call(self.w_fun, w_objects)

    def _get_objects(self):
        # the loop is out of the way of the JIT
        return [self.space.next(w_elem) for w_elem in self.iterators_w]


def W_IMap___new__(space, w_subtype, w_fun, args_w):
    if len(args_w) == 0:
        raise OperationError(space.w_TypeError,
                  space.wrap("imap() must have at least two arguments"))
    r = space.allocate_instance(W_IMap, w_subtype)
    r.__init__(space, w_fun, args_w)
    return space.wrap(r)

W_IMap.typedef = TypeDef(
        'imap',
        __module__ = 'itertools',
        __new__  = interp2app(W_IMap___new__),
        __iter__ = interp2app(W_IMap.iter_w),
        next     = interp2app(W_IMap.next_w),
        __doc__  = """Make an iterator that computes the function using arguments
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

    """)


class W_IZip(W_IMap):
    _error_name = "izip"

    def next_w(self):
        # argh.  izip(*args) is almost like imap(None, *args) except
        # that the former needs a special case for len(args)==0
        # while the latter just raises a TypeError in this situation.
        if len(self.iterators_w) == 0:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        return W_IMap.next_w(self)

def W_IZip___new__(space, w_subtype, args_w):
    r = space.allocate_instance(W_IZip, w_subtype)
    r.__init__(space, space.w_None, args_w)
    return space.wrap(r)

W_IZip.typedef = TypeDef(
        'izip',
        __module__ = 'itertools',
        __new__  = interp2app(W_IZip___new__),
        __iter__ = interp2app(W_IZip.iter_w),
        next     = interp2app(W_IZip.next_w),
        __doc__  = """Make an iterator that aggregates elements from each of the
    iterables.  Like zip() except that it returns an iterator instead
    of a list. Used for lock-step iteration over several iterables at
    a time.

    Equivalent to :

    def izip(*iterables):
        iterables = map(iter, iterables)
        while iterables:
            result = [i.next() for i in iterables]
            yield tuple(result)
    """)


class W_IZipLongest(W_IMap):
    _error_name = "izip_longest"

    def next_w(self):
        space = self.space
        nb = len(self.iterators_w)

        if nb == 0:
            raise OperationError(space.w_StopIteration, space.w_None)

        objects_w = [None] * nb
        for index in range(nb):
            w_value = self.w_fillvalue
            w_it = self.iterators_w[index]
            if w_it is not None:
                try:
                    w_value = space.next(w_it)
                except OperationError, e:
                    if not e.match(space, space.w_StopIteration):
                        raise

                    self.active -= 1
                    if self.active == 0:
                        # It was the last active iterator
                        raise
                    self.iterators_w[index] = None

            objects_w[index] = w_value
        return space.newtuple(objects_w)

def W_IZipLongest___new__(space, w_subtype, __args__):
    arguments_w, kwds_w = __args__.unpack()
    w_fillvalue = space.w_None
    if kwds_w:
        if "fillvalue" in kwds_w:
            w_fillvalue = kwds_w["fillvalue"]
            del kwds_w["fillvalue"]
        if kwds_w:
            raise OperationError(space.w_TypeError, space.wrap(
                "izip_longest() got unexpected keyword argument(s)"))

    self = space.allocate_instance(W_IZipLongest, w_subtype)
    self.__init__(space, space.w_None, arguments_w)
    self.w_fillvalue = w_fillvalue
    self.active = len(self.iterators_w)

    return space.wrap(self)

W_IZipLongest.typedef = TypeDef(
        'izip_longest',
        __module__ = 'itertools',
        __new__  = interp2app(W_IZipLongest___new__),
        __iter__ = interp2app(W_IZipLongest.iter_w),
        next     = interp2app(W_IZipLongest.next_w),
        __doc__  = """Return an izip_longest object whose .next() method returns a tuple where
    the i-th element comes from the i-th iterable argument.  The .next()
    method continues until the longest iterable in the argument sequence
    is exhausted and then it raises StopIteration.  When the shorter iterables
    are exhausted, the fillvalue is substituted in their place.  The fillvalue
    defaults to None or can be specified by a keyword argument.
    """)


class W_Cycle(Wrappable):

    def __init__(self, space, w_iterable):
        self.space = space
        self.saved_w = []
        self.w_iterable = space.iter(w_iterable)
        self.index = 0
        self.exhausted = False

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.exhausted:
            if not self.saved_w:
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            try:
                w_obj = self.saved_w[self.index]
            except IndexError:
                self.index = 1
                w_obj = self.saved_w[0]
            else:
                self.index += 1
        else:
            try:
                w_obj = self.space.next(self.w_iterable)
            except OperationError, e:
                if e.match(self.space, self.space.w_StopIteration):
                    self.exhausted = True
                    if not self.saved_w:
                        raise
                    self.index = 1
                    w_obj = self.saved_w[0]
                else:
                    raise
            else:
                self.index += 1
                self.saved_w.append(w_obj)
        return w_obj

def W_Cycle___new__(space, w_subtype, w_iterable):
    r = space.allocate_instance(W_Cycle, w_subtype)
    r.__init__(space, w_iterable)
    return space.wrap(r)

W_Cycle.typedef = TypeDef(
        'cycle',
        __module__ = 'itertools',
        __new__  = interp2app(W_Cycle___new__),
        __iter__ = interp2app(W_Cycle.iter_w),
        next     = interp2app(W_Cycle.next_w),
        __doc__  = """Make an iterator returning elements from the iterable and
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
    """)

class W_StarMap(Wrappable):

    def __init__(self, space, w_fun, w_iterable):
        self.space = space
        self.w_fun = w_fun
        self.w_iterable = self.space.iter(w_iterable)

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        w_obj = self.space.next(self.w_iterable)
        return self.space.call(self.w_fun, w_obj)

def W_StarMap___new__(space, w_subtype, w_fun, w_iterable):
    r = space.allocate_instance(W_StarMap, w_subtype)
    r.__init__(space, w_fun, w_iterable)
    return space.wrap(r)

W_StarMap.typedef = TypeDef(
        'starmap',
        __module__ = 'itertools',
        __new__  = interp2app(W_StarMap___new__),
        __iter__ = interp2app(W_StarMap.iter_w),
        next     = interp2app(W_StarMap.next_w),
        __doc__  = """Make an iterator that computes the function using arguments
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
    """)


@unwrap_spec(n=int)
def tee(space, w_iterable, n=2):
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
        raise OperationError(space.w_ValueError, space.wrap("n must be >= 0"))

    myiter = space.interpclass_w(w_iterable)
    if isinstance(myiter, W_TeeIterable):     # optimization only
        tee_state = myiter.tee_state
        iterators_w = [w_iterable] * n
        for i in range(1, n):
            iterators_w[i] = space.wrap(W_TeeIterable(space, tee_state))
    else:
        tee_state = TeeState(space, w_iterable)
        iterators_w = [space.wrap(W_TeeIterable(space, tee_state)) for x in range(n)]
    return space.newtuple(iterators_w)

class TeeState(object):
    def __init__(self, space, w_iterable):
        self.space = space
        self.w_iterable = self.space.iter(w_iterable)
        self.num_saved = 0
        self.saved_w = []

    def get_next(self, index):
        if index >= self.num_saved:
            w_obj = self.space.next(self.w_iterable)
            self.saved_w.append(w_obj)
            self.num_saved += 1
            return w_obj
        else:
            return self.saved_w[index]

class W_TeeIterable(Wrappable):
    def __init__(self, space, tee_state):
        self.space = space
        self.tee_state = tee_state
        self.index = 0

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        try:
            w_obj = self.tee_state.get_next(self.index)
            return w_obj
        finally:
            self.index += 1

def W_TeeIterable___new__(space, w_subtype, w_iterable):
    # Obscure and undocumented function.  PyPy only supports w_iterable
    # being a W_TeeIterable, because the case where it is a general
    # iterable is useless and confusing as far as I can tell (as the
    # semantics are then slightly different; see the XXX in lib-python's
    # test_itertools).
    myiter = space.interp_w(W_TeeIterable, w_iterable)
    tee_state = myiter.tee_state
    return space.wrap(W_TeeIterable(space, tee_state))

W_TeeIterable.typedef = TypeDef(
        '_tee',
        __module__ = 'itertools',
        __new__ = interp2app(W_TeeIterable___new__),
        __iter__ = interp2app(W_TeeIterable.iter_w),
        next     = interp2app(W_TeeIterable.next_w),
        __weakref__ = make_weakref_descr(W_TeeIterable),
        )
W_TeeIterable.typedef.acceptable_as_base_class = False


class W_GroupBy(Wrappable):

    def __init__(self, space, w_iterable, w_fun):
        self.space = space
        self.w_iterable = self.space.iter(w_iterable)
        self.identity_fun = self.space.is_w(w_fun, self.space.w_None)
        self.w_fun = w_fun
        self.index = 0
        self.lookahead = False
        self.exhausted = False
        self.started = False
        # new_group - new group not started yet, next should not skip any items
        self.new_group = True
        self.w_lookahead = self.space.w_None
        self.w_key = self.space.w_None

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.exhausted:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        if not self.new_group:
            self._consume_unwanted_input()

        if not self.started:
            self.started = True
            try:
                w_obj = self.space.next(self.w_iterable)
            except OperationError, e:
                if e.match(self.space, self.space.w_StopIteration):
                    self.exhausted = True
                raise
            else:
                self.w_lookahead = w_obj
                if self.identity_fun:
                    self.w_key = w_obj
                else:
                    self.w_key = self.space.call_function(self.w_fun, w_obj)
                self.lookahead = True

        self.new_group = False
        w_iterator = self.space.wrap(W_GroupByIterator(self.space, self.index, self))
        return self.space.newtuple([self.w_key, w_iterator])

    def _consume_unwanted_input(self):
        # Consume unwanted input until we reach the next group
        try:
            while True:
                self.group_next(self.index)
        except StopIteration:
            pass
        if self.exhausted:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

    def group_next(self, group_index):
        if group_index < self.index:
            raise StopIteration
        else:
            if self.lookahead:
                self.lookahead = False
                return self.w_lookahead

            try:
                w_obj = self.space.next(self.w_iterable)
            except OperationError, e:
                if e.match(self.space, self.space.w_StopIteration):
                    self.exhausted = True
                    raise StopIteration
                else:
                    raise
            else:
                if self.identity_fun:
                    w_new_key = w_obj
                else:
                    w_new_key = self.space.call_function(self.w_fun, w_obj)
                if self.space.eq_w(self.w_key, w_new_key):
                    return w_obj
                else:
                    self.index += 1
                    self.w_lookahead = w_obj
                    self.w_key = w_new_key
                    self.lookahead = True
                    self.new_group = True #new group
                    raise StopIteration

def W_GroupBy___new__(space, w_subtype, w_iterable, w_key=None):
    r = space.allocate_instance(W_GroupBy, w_subtype)
    r.__init__(space, w_iterable, w_key)
    return space.wrap(r)

W_GroupBy.typedef = TypeDef(
        'groupby',
        __module__ = 'itertools',
        __new__  = interp2app(W_GroupBy___new__),
        __iter__ = interp2app(W_GroupBy.iter_w),
        next     = interp2app(W_GroupBy.next_w),
        __doc__  = """Make an iterator that returns consecutive keys and groups from the
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
    """)

class W_GroupByIterator(Wrappable):
    def __init__(self, space, index, groupby):
        self.space = space
        self.index = index
        self.groupby = groupby
        self.exhausted = False

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.exhausted:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        try:
            w_obj = self.groupby.group_next(self.index)
        except StopIteration:
            self.exhausted = True
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        else:
            return w_obj

W_GroupByIterator.typedef = TypeDef(
        '_groupby',
        __module__ = 'itertools',
        __iter__ = interp2app(W_GroupByIterator.iter_w),
        next     = interp2app(W_GroupByIterator.next_w))
W_GroupByIterator.typedef.acceptable_as_base_class = False


class W_Compress(Wrappable):
    def __init__(self, space, w_data, w_selectors):
        self.space = space
        self.w_data = space.iter(w_data)
        self.w_selectors = space.iter(w_selectors)

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        # No need to check for StopIteration since either w_data
        # or w_selectors will raise this. The shortest one stops first.
        while True:
            w_next_item = self.space.next(self.w_data)
            w_next_selector = self.space.next(self.w_selectors)
            if self.space.is_true(w_next_selector):
                return w_next_item


def W_Compress__new__(space, w_subtype, w_data, w_selectors):
    r = space.allocate_instance(W_Compress, w_subtype)
    r.__init__(space, w_data, w_selectors)
    return space.wrap(r)

W_Compress.typedef = TypeDef(
    'compress',
    __module__ = 'itertools',
    __new__ = interp2app(W_Compress__new__),
    __iter__ = interp2app(W_Compress.iter_w),
    next     = interp2app(W_Compress.next_w),
    __doc__ = """Make an iterator that filters elements from *data* returning
   only those that have a corresponding element in *selectors* that evaluates to
   ``True``.  Stops when either the *data* or *selectors* iterables has been
   exhausted.
   Equivalent to::

       def compress(data, selectors):
           # compress('ABCDEF', [1,0,1,0,1,1]) --> A C E F
           return (d for d, s in izip(data, selectors) if s)
""")


class W_Product(Wrappable):
    def __init__(self, space, args_w, w_repeat):
        self.gears = [
            space.fixedview(arg_w) for arg_w in args_w
        ] * space.int_w(w_repeat)
        self.num_gears = len(self.gears)
        # initialization of indicies to loop over
        self.indicies = [
            (0, len(gear))
            for gear in self.gears
        ]
        self.cont = True
        for _, lim in self.indicies:
            if lim <= 0:
                self.cont = False
                break

    def roll_gears(self):
        if self.num_gears == 0:
            self.cont = False
            return

        # Starting from the end of the gear indicies work to the front
        # incrementing the gear until the limit is reached. When the limit
        # is reached carry operation to the next gear
        should_carry = True

        for n in range(0, self.num_gears):
            nth_gear = self.num_gears - n - 1
            if should_carry:
                count, lim = self.indicies[nth_gear]
                count += 1
                if count == lim and nth_gear == 0:
                    self.cont = False
                if count == lim:
                    should_carry = True
                    count = 0
                else:
                    should_carry = False
                self.indicies[nth_gear] = (count, lim)
            else:
                break

    def iter_w(self, space):
        return space.wrap(self)

    def next_w(self, space):
        if not self.cont:
            raise OperationError(space.w_StopIteration, space.w_None)
        l = [None] * self.num_gears
        for x in range(0, self.num_gears):
            index, limit = self.indicies[x]
            l[x] = self.gears[x][index]
        self.roll_gears()
        return space.newtuple(l)


def W_Product__new__(space, w_subtype, __args__):
    arguments_w, kwds_w = __args__.unpack()
    w_repeat = space.wrap(1)
    if kwds_w:
        if 'repeat' in kwds_w:
            w_repeat = kwds_w['repeat']
            del kwds_w['repeat']
        if kwds_w:
            raise OperationError(space.w_TypeError, space.wrap(
                "product() got unexpected keyword argument(s)"))

    r = space.allocate_instance(W_Product, w_subtype)
    r.__init__(space, arguments_w, w_repeat)
    return space.wrap(r)

W_Product.typedef = TypeDef(
    'product',
    __module__ = 'itertools',
    __new__ = interp2app(W_Product__new__),
    __iter__ = interp2app(W_Product.iter_w),
    next = interp2app(W_Product.next_w),
    __doc__ = """
   Cartesian product of input iterables.

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
""")


class W_Combinations(Wrappable):
    def __init__(self, space, pool_w, indices, r):
        self.pool_w = pool_w
        self.indices = indices
        self.r = r
        self.last_result_w = None
        self.stopped = r > len(pool_w)

    def get_maximum(self, i):
        return i + len(self.pool_w) - self.r

    def max_index(self, j):
        return self.indices[j - 1] + 1

    def descr__iter__(self, space):
        return self

    def descr_next(self, space):
        if self.stopped:
            raise OperationError(space.w_StopIteration, space.w_None)
        if self.last_result_w is None:
            # On the first pass, initialize result tuple using the indices
            result_w = [None] * self.r
            for i in xrange(self.r):
                index = self.indices[i]
                result_w[i] = self.pool_w[index]
        else:
            # Copy the previous result
            result_w = self.last_result_w[:]
            # Scan indices right-to-left until finding one that is not at its
            # maximum
            i = self.r - 1
            while i >= 0 and self.indices[i] == self.get_maximum(i):
                i -= 1

            # If i is negative, then the indices are all at their maximum value
            # and we're done
            if i < 0:
                self.stopped = True
                raise OperationError(space.w_StopIteration, space.w_None)

            # Increment the current index which we know is not at its maximum.
            # Then move back to the right setting each index to its lowest
            # possible value
            self.indices[i] += 1
            for j in xrange(i + 1, self.r):
                self.indices[j] = self.max_index(j)

            # Update the result for the new indices starting with i, the
            # leftmost index that changed
            for i in xrange(i, self.r):
                index = self.indices[i]
                w_elem = self.pool_w[index]
                result_w[i] = w_elem
        self.last_result_w = result_w
        return space.newtuple(result_w)

@unwrap_spec(r=int)
def W_Combinations__new__(space, w_subtype, w_iterable, r):
    pool_w = space.fixedview(w_iterable)
    if r < 0:
        raise OperationError(space.w_ValueError,
            space.wrap("r must be non-negative")
        )
    indices = range(len(pool_w))
    res = space.allocate_instance(W_Combinations, w_subtype)
    res.__init__(space, pool_w, indices, r)
    return space.wrap(res)

W_Combinations.typedef = TypeDef("combinations",
    __module__ = 'itertools',
    __new__ = interp2app(W_Combinations__new__),
    __iter__ = interp2app(W_Combinations.descr__iter__),
    next = interp2app(W_Combinations.descr_next),
    __doc__ = """\
combinations(iterable, r) --> combinations object

Return successive r-length combinations of elements in the iterable.

combinations(range(4), 3) --> (0,1,2), (0,1,3), (0,2,3), (1,2,3)""",
)

class W_CombinationsWithReplacement(W_Combinations):
    def __init__(self, space, pool_w, indices, r):
        W_Combinations.__init__(self, space, pool_w, indices, r)
        self.stopped = len(pool_w) == 0 and r > 0

    def get_maximum(self, i):
        return len(self.pool_w) - 1

    def max_index(self, j):
        return self.indices[j - 1]

@unwrap_spec(r=int)
def W_CombinationsWithReplacement__new__(space, w_subtype, w_iterable, r):
    pool_w = space.fixedview(w_iterable)
    if r < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("r must be non-negative"))
    indices = [0] * r
    res = space.allocate_instance(W_CombinationsWithReplacement, w_subtype)
    res.__init__(space, pool_w, indices, r)
    return space.wrap(res)

W_CombinationsWithReplacement.typedef = TypeDef("combinations_with_replacement",
    __module__ = 'itertools',
    __new__ = interp2app(W_CombinationsWithReplacement__new__),
    __iter__ = interp2app(W_CombinationsWithReplacement.descr__iter__),
    next = interp2app(W_CombinationsWithReplacement.descr_next),
    __doc__ = """\
combinations_with_replacement(iterable, r) --> combinations_with_replacement object

Return successive r-length combinations of elements in the iterable
allowing individual elements to have successive repeats.
combinations_with_replacement('ABC', 2) --> AA AB AC BB BC CC""",
)


class W_Permutations(Wrappable):
    def __init__(self, space, pool_w, r):
        self.pool_w = pool_w
        self.r = r
        n = len(pool_w)
        n_minus_r = n - r
        if n_minus_r < 0:
            self.stopped = True
        else:
            self.stopped = False
            self.indices = range(n)
            self.cycles = range(n, n_minus_r, -1)

    def descr__iter__(self, space):
        return self

    def descr_next(self, space):
        if self.stopped:
            raise OperationError(space.w_StopIteration, space.w_None)
        r = self.r
        indices = self.indices
        w_result = space.newtuple([self.pool_w[indices[i]]
                                   for i in range(r)])
        cycles = self.cycles
        i = r - 1
        while i >= 0:
            j = cycles[i] - 1
            if j > 0:
                cycles[i] = j
                indices[i], indices[-j] = indices[-j], indices[i]
                return w_result
            cycles[i] = len(indices) - i
            n1 = len(indices) - 1
            assert n1 >= 0
            num = indices[i]
            for k in range(i, n1):
                indices[k] = indices[k+1]
            indices[n1] = num
            i -= 1
        self.stopped = True
        return w_result

def W_Permutations__new__(space, w_subtype, w_iterable, w_r=None):
    pool_w = space.fixedview(w_iterable)
    if space.is_w(w_r, space.w_None):
        r = len(pool_w)
    else:
        r = space.gateway_nonnegint_w(w_r)
    res = space.allocate_instance(W_Permutations, w_subtype)
    res.__init__(space, pool_w, r)
    return space.wrap(res)

W_Permutations.typedef = TypeDef("permutations",
    __module__ = 'itertools',
    __new__ = interp2app(W_Permutations__new__),
    __iter__ = interp2app(W_Permutations.descr__iter__),
    next = interp2app(W_Permutations.descr_next),
    __doc__ = """\
permutations(iterable[, r]) --> permutations object

Return successive r-length permutations of elements in the iterable.

permutations(range(3), 2) --> (0,1), (0,2), (1,0), (1,2), (2,0), (2,1)""",
)
