"""
Interp-level definition of frequently used functionals.

"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, applevel
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.module.__builtin__.app_functional import range as app_range
from inspect import getsource, getfile

"""
Implementation of the common integer case of range. Instead of handling
all other cases here, too, we fall back to the applevel implementation
for non-integer arguments.
Ideally this implementation could be saved, if we were able to
specialize the geninterp generated code. But I guess having this
hand-optimized is a good idea.

Note the fun of using range inside range :-)
"""

def get_len_of_range(lo, hi, step):
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
        raise ValueError
    elif step < 0:
        lo, hi, step = hi, lo, -step
    if lo < hi:
        uhi = r_uint(hi)
        ulo = r_uint(lo)
        diff = uhi - ulo - 1
        n = intmask(diff // r_uint(step) + 1)
        if n < 0:
            raise OverflowError
    else:
        n = 0
    return n

def range(space, w_x, w_y=None, w_step=1):
    """Return a list of integers in arithmetic position from start (defaults
to zero) to stop - 1 by step (defaults to 1).  Use a negative step to
get a list in decending order."""

    try:
        # save duplication by redirecting every error to applevel
        x = space.int_w(w_x)
        if space.is_w(w_y, space.w_None):
            start, stop = 0, x
        else:
            start, stop = x, space.int_w(w_y)
        step = space.int_w(w_step)
        howmany = get_len_of_range(start, stop, step)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            pass
        else:
            raise
    except (ValueError, OverflowError):
        pass
    else:
        if (space.config.objspace.std.withmultilist or
            space.config.objspace.std.withrangelist):
            return range_withspecialized_implementation(space, start,
                                                        step, howmany)
        res_w = [None] * howmany
        v = start
        for idx in range(howmany):
            res_w[idx] = space.wrap(v)
            v += step
        return space.newlist(res_w)
    return range_fallback(space, w_x, w_y, w_step)
range_int = range
range_int.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]
del range # don't hide the builtin one

range_fallback = applevel(getsource(app_range), getfile(app_range)
                          ).interphook('range')

def range_withspecialized_implementation(space, start, step, howmany):
    if space.config.objspace.std.withrangelist:
        from pypy.objspace.std.rangeobject import W_RangeListObject
        return W_RangeListObject(start, step, howmany)
    if space.config.objspace.std.withmultilist:
        from pypy.objspace.std.listmultiobject import W_ListMultiObject
        from pypy.objspace.std.listmultiobject import RangeImplementation
        impl = RangeImplementation(space, start, step, howmany)
        return W_ListMultiObject(space, impl)




def all(space, w_S):
    """all(iterable) -> bool

Return True if bool(x) is True for all values x in the iterable."""
    w_iter = space.iter(w_S)
    while True:
        try:
            w_next = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise       # re-raise other app-level exceptions
            break
        if not space.is_true(w_next):
            return space.w_False
    return space.w_True
all.unwrap_spec = [ObjSpace, W_Root]


def any(space, w_S):
    """any(iterable) -> bool

Return True if bool(x) is True for any x in the iterable."""
    w_iter = space.iter(w_S)
    while True:
        try:
            w_next = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise       # re-raise other app-level exceptions
            break
        if space.is_true(w_next):
            return space.w_True
    return space.w_False
any.unwrap_spec = [ObjSpace, W_Root]


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
        try:
            howmany = get_len_of_range(start, stop, step)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("xrange() arg 3 must not be zero"))
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                                 space.wrap("xrange() result has "
                                            "too many items"))
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

def _toint(space, w_obj):
    # trying to support float arguments, just because CPython still does
    try:
        return space.int_w(w_obj)
    except OperationError, e:
        if space.is_true(space.isinstance(w_obj, space.w_float)):
            return space.int_w(space.int(w_obj))
        raise

W_XRange.typedef = TypeDef("xrange",
    __new__          = interp2app(W_XRange.descr_new.im_func),
    __repr__         = interp2app(W_XRange.descr_repr),
    __getitem__      = interp2app(W_XRange.descr_getitem, 
                                  unwrap_spec=['self', 'index']),
    __iter__         = interp2app(W_XRange.descr_iter),
    __len__          = interp2app(W_XRange.descr_len),
    __reversed__     = interp2app(W_XRange.descr_reversed),
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
        from pypy.module._pickle_support import maker # helper fns
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
    __len__         = interp2app(W_XRangeIterator.descr_len),
    next            = interp2app(W_XRangeIterator.descr_next),
    __reduce__      = interp2app(W_XRangeIterator.descr_reduce),
)
