"""
Interp-level definition of frequently used functionals.

"""

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.rbigint import rbigint


def get_len_of_range(space, lo, hi, step):
    """
    Return number of items in range/xrange (lo, hi, step).
    Raise ValueError if step == 0 and OverflowError if the true value is too
    large to fit in a signed long.
    """

    # If lo >= hi, the range is empty.
    # Else if n values are in the range, the last one is
    # lo + (n-1)*step, which must be <= hi-1.  Rearranging,
    # n <= (hi - lo - 1)/step + 1, so taking the floor of the RHS gives
    # the proper value.  Since lo < hi in this case, hi-lo-1 >= 0, so
    # the RHS is non-negative and so truncation is the same as the
    # floor.  Letting M be the largest positive long, the worst case
    # for the RHS numerator is hi=M, lo=-M-1, and then
    # hi-lo-1 = M-(-M-1)-1 = 2*M.  Therefore unsigned long has enough
    # precision to compute the RHS exactly.
    if step == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("step argument must not be zero"))
    elif step < 0:
        lo, hi, step = hi, lo, -step
    if lo < hi:
        uhi = r_uint(hi)
        ulo = r_uint(lo)
        diff = uhi - ulo - 1
        n = intmask(diff // r_uint(step) + 1)
        if n < 0:
            raise OperationError(space.w_OverflowError,
                                 space.wrap("result has too many items"))
    else:
        n = 0
    return n

def range_int(space, w_x, w_y=NoneNotWrapped, w_step=1):
    """Return a list of integers in arithmetic position from start (defaults
to zero) to stop - 1 by step (defaults to 1).  Use a negative step to
get a list in decending order."""

    if w_y is None:
        w_start = space.wrap(0)
        w_stop = w_x
    else:
        w_start = w_x
        w_stop = w_y

    if space.is_true(space.isinstance(w_stop, space.w_float)):
        raise OperationError(space.w_TypeError,
            space.wrap("range() integer end argument expected, got float."))
    if space.is_true(space.isinstance(w_start, space.w_float)):
        raise OperationError(space.w_TypeError,
            space.wrap("range() integer start argument expected, got float."))
    if space.is_true(space.isinstance(w_step, space.w_float)):
        raise OperationError(space.w_TypeError,
            space.wrap("range() integer step argument expected, got float."))

    w_start = space.int(w_start)
    w_stop  = space.int(w_stop)
    w_step  = space.int(w_step)

    try:
        start = space.int_w(w_start)
        stop  = space.int_w(w_stop)
        step  = space.int_w(w_step)
    except OperationError, e:
        if not e.match(space, space.w_OverflowError):
            raise
        return range_with_longs(space, w_start, w_stop, w_step)

    howmany = get_len_of_range(space, start, stop, step)

    if space.config.objspace.std.withrangelist:
        return range_withspecialized_implementation(space, start,
                                                    step, howmany)
    res_w = [None] * howmany
    v = start
    for idx in range(howmany):
        res_w[idx] = space.wrap(v)
        v += step
    return space.newlist(res_w)


def range_withspecialized_implementation(space, start, step, howmany):
    assert space.config.objspace.std.withrangelist
    from pypy.objspace.std.rangeobject import W_RangeListObject
    return W_RangeListObject(start, step, howmany)

bigint_one = rbigint.fromint(1)

def range_with_longs(space, w_start, w_stop, w_step):

    start = lo = space.bigint_w(w_start)
    stop  = hi = space.bigint_w(w_stop)
    step  = st = space.bigint_w(w_step)

    if not step.tobool():
        raise OperationError(space.w_ValueError,
                             space.wrap("step argument must not be zero"))
    elif step.sign < 0:
        lo, hi, st = hi, lo, st.neg()

    if lo.lt(hi):
        diff = hi.sub(lo).sub(bigint_one)
        n = diff.floordiv(st).add(bigint_one)
        try:
            howmany = n.toint()
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                                 space.wrap("result has too many items"))
    else:
        howmany = 0

    res_w = [None] * howmany
    v = start
    for idx in range(howmany):
        res_w[idx] = space.newlong_from_rbigint(v)
        v = v.add(step)
    return space.newlist(res_w)


@specialize.arg(2)
@jit.look_inside_iff(lambda space, args, implementation_of:
    jit.isconstant(len(args.arguments_w)) and
    len(args.arguments_w) == 2
)
def min_max(space, args, implementation_of):
    if implementation_of == "max":
        compare = space.gt
    else:
        compare = space.lt
    args_w = args.arguments_w
    if len(args_w) > 1:
        w_sequence = space.newtuple(args_w)
    elif len(args_w):
        w_sequence = args_w[0]
    else:
        msg = "%s() expects at least one argument" % (implementation_of,)
        raise OperationError(space.w_TypeError, space.wrap(msg))
    w_key = None
    kwds = args.keywords
    if kwds:
        if kwds[0] == "key" and len(kwds) == 1:
            w_key = args.keywords_w[0]
        else:
            msg = "%s() got unexpected keyword argument" % (implementation_of,)
            raise OperationError(space.w_TypeError, space.wrap(msg))

    w_iter = space.iter(w_sequence)
    w_max_item = None
    w_max_val = None
    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        if w_key is not None:
            w_compare_with = space.call_function(w_key, w_item)
        else:
            w_compare_with = w_item
        if w_max_item is None or \
                space.is_true(compare(w_compare_with, w_max_val)):
            w_max_item = w_item
            w_max_val = w_compare_with
    if w_max_item is None:
        msg = "arg is an empty sequence"
        raise OperationError(space.w_ValueError, space.wrap(msg))
    return w_max_item

def max(space, __args__):
    """max(iterable[, key=func]) -> value
    max(a, b, c, ...[, key=func]) -> value

    With a single iterable argument, return its largest item.
    With two or more arguments, return the largest argument.
    """
    return min_max(space, __args__, "max")

def min(space, __args__):
    """min(iterable[, key=func]) -> value
    min(a, b, c, ...[, key=func]) -> value

    With a single iterable argument, return its smallest item.
    With two or more arguments, return the smallest argument.
    """
    return min_max(space, __args__, "min")

class W_Enumerate(Wrappable):

    def __init__(self, w_iter, w_start):
        self.w_iter = w_iter
        self.w_index = w_start

    def descr___new__(space, w_subtype, w_iterable, w_start=NoneNotWrapped):
        self = space.allocate_instance(W_Enumerate, w_subtype)
        if w_start is None:
            w_start = space.wrap(0)
        else:
            w_start = space.index(w_start)
        self.__init__(space.iter(w_iterable), w_start)
        return space.wrap(self)

    def descr___iter__(self, space):
        return space.wrap(self)

    def descr_next(self, space):
        w_item = space.next(self.w_iter)
        w_index = self.w_index
        self.w_index = space.add(w_index, space.wrap(1))
        return space.newtuple([w_index, w_item])

    def descr___reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        w_new_inst = mod.get('enumerate_new')
        w_info = space.newtuple([self.w_iter, self.w_index])
        return space.newtuple([w_new_inst, w_info])

# exported through _pickle_support
def _make_enumerate(space, w_iter, w_index):
    return space.wrap(W_Enumerate(w_iter, w_index))

W_Enumerate.typedef = TypeDef("enumerate",
    __new__=interp2app(W_Enumerate.descr___new__.im_func),
    __iter__=interp2app(W_Enumerate.descr___iter__),
    next=interp2app(W_Enumerate.descr_next),
    __reduce__=interp2app(W_Enumerate.descr___reduce__),
)


def reversed(space, w_sequence):
    """Return a iterator that yields items of sequence in reverse."""
    w_reversed = None
    if space.is_oldstyle_instance(w_sequence):
        w_reversed = space.findattr(w_sequence, space.wrap("__reversed__"))
    else:
        w_reversed_descr = space.lookup(w_sequence, "__reversed__")
        if w_reversed_descr is not None:
            w_reversed = space.get(w_reversed_descr, w_sequence)
    if w_reversed is not None:
        return space.call_function(w_reversed)
    return space.wrap(W_ReversedIterator(space, w_sequence))

class W_ReversedIterator(Wrappable):

    def __init__(self, space, w_sequence):
        self.remaining = space.len_w(w_sequence) - 1
        if space.lookup(w_sequence, "__getitem__") is None:
            msg = "reversed() argument must be a sequence"
            raise OperationError(space.w_TypeError, space.wrap(msg))
        self.w_sequence = w_sequence

    def descr___iter__(self, space):
        return space.wrap(self)

    def descr_next(self, space):
        if self.remaining >= 0:
            w_index = space.wrap(self.remaining)
            try:
                w_item = space.getitem(self.w_sequence, w_index)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
            else:
                self.remaining -= 1
                return w_item

        # Done
        self.remaining = -1
        raise OperationError(space.w_StopIteration, space.w_None)

    def descr___reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        w_new_inst = mod.get('reversed_new')
        info_w = [self.w_sequence, space.wrap(self.remaining)]
        w_info = space.newtuple(info_w)
        return space.newtuple([w_new_inst, w_info])

W_ReversedIterator.typedef = TypeDef("reversed",
    __iter__=interp2app(W_ReversedIterator.descr___iter__),
    next=interp2app(W_ReversedIterator.descr_next),
    __reduce__=interp2app(W_ReversedIterator.descr___reduce__),
)

# exported through _pickle_support
def _make_reversed(space, w_seq, w_remaining):
    w_type = space.gettypeobject(W_ReversedIterator.typedef)
    iterator = space.allocate_instance(W_ReversedIterator, w_type)
    iterator.w_sequence = w_seq
    iterator.remaining = space.int_w(w_remaining)
    return space.wrap(iterator)



class W_XRange(Wrappable):
    def __init__(self, space, start, len, step):
        self.space = space
        self.start = start
        self.len   = len
        self.step  = step

    def descr_new(space, w_subtype, w_start, w_stop=None, w_step=1):
        start = _toint(space, w_start)
        step  = _toint(space, w_step)
        if space.is_w(w_stop, space.w_None):  # only 1 argument provided
            start, stop = 0, start
        else:
            stop = _toint(space, w_stop)
        howmany = get_len_of_range(space, start, stop, step)
        obj = space.allocate_instance(W_XRange, w_subtype)
        W_XRange.__init__(obj, space, start, howmany, step)
        return space.wrap(obj)

    def descr_repr(self):
        stop = self.start + self.len * self.step
        if self.start == 0 and self.step == 1:
            s = "xrange(%d)" % (stop,)
        elif self.step == 1:
            s = "xrange(%d, %d)" % (self.start, stop)
        else:
            s = "xrange(%d, %d, %d)" %(self.start, stop, self.step)
        return self.space.wrap(s)

    def descr_len(self):
        return self.space.wrap(self.len)

    @unwrap_spec(i='index')
    def descr_getitem(self, i):
        # xrange does NOT support slicing
        space = self.space
        len = self.len
        if i < 0:
            i += len
        if 0 <= i < len:
            return space.wrap(self.start + i * self.step)
        raise OperationError(space.w_IndexError,
                             space.wrap("xrange object index out of range"))

    def descr_iter(self):
        return self.space.wrap(W_XRangeIterator(self.space, self.start,
                                                self.len, self.step))

    def descr_reversed(self):
        lastitem = self.start + (self.len-1) * self.step
        return self.space.wrap(W_XRangeIterator(self.space, lastitem,
                                                self.len, -self.step))

    def descr_reduce(self):
        space = self.space
        return space.newtuple(
            [space.type(self),
             space.newtuple([space.wrap(self.start),
                             space.wrap(self.start + self.len * self.step),
                             space.wrap(self.step)])
             ])

def _toint(space, w_obj):
    # this also supports float arguments.  CPython still does, too.
    # needs a bit more thinking in general...
    return space.int_w(space.int(w_obj))

W_XRange.typedef = TypeDef("xrange",
    __new__          = interp2app(W_XRange.descr_new.im_func),
    __repr__         = interp2app(W_XRange.descr_repr),
    __getitem__      = interp2app(W_XRange.descr_getitem),
    __iter__         = interp2app(W_XRange.descr_iter),
    __len__          = interp2app(W_XRange.descr_len),
    __reversed__     = interp2app(W_XRange.descr_reversed),
    __reduce__       = interp2app(W_XRange.descr_reduce),
)

class W_XRangeIterator(Wrappable):
    def __init__(self, space, current, remaining, step):
        self.space = space
        self.current = current
        self.remaining = remaining
        self.step = step

    def descr_iter(self):
        return self.space.wrap(self)

    def descr_next(self):
        if self.remaining > 0:
            item = self.current
            self.current = item + self.step
            self.remaining -= 1
            return self.space.wrap(item)
        raise OperationError(self.space.w_StopIteration, self.space.w_None)

    def descr_len(self):
        return self.space.wrap(self.remaining)

    def descr_reduce(self):
        from pypy.interpreter.mixedmodule import MixedModule
        space    = self.space
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('xrangeiter_new')
        w        = space.wrap
        nt = space.newtuple

        tup = [w(self.current), w(self.remaining), w(self.step)]
        return nt([new_inst, nt(tup)])

W_XRangeIterator.typedef = TypeDef("rangeiterator",
    __iter__        = interp2app(W_XRangeIterator.descr_iter),
# XXX __length_hint__()
##    __len__         = interp2app(W_XRangeIterator.descr_len),
    next            = interp2app(W_XRangeIterator.descr_next),
    __reduce__      = interp2app(W_XRangeIterator.descr_reduce),
)
