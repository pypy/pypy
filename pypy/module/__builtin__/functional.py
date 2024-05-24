"""
Interp-level definition of frequently used functionals.

"""
import sys

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    interp2app, interpindirect2app, unwrap_spec,
    WrappedDefault)
from pypy.interpreter.typedef import TypeDef, interp_attrproperty_w
from rpython.rlib import jit, rarithmetic
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_uint, intmask
from pypy.objspace.std.util import generic_alias_class_getitem


def get_len_of_range(lo, hi, step):
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
    assert step != 0
    if step < 0:
        lo, hi, step = hi, lo, -step
    if lo < hi:
        uhi = r_uint(hi)
        ulo = r_uint(lo)
        diff = uhi - ulo - 1
        n = intmask(diff // r_uint(step) + 1)
    else:
        n = 0
    return n

def compute_range_length(space, w_start, w_stop, w_step):
    # Algorithm is equal to that of get_len_of_range(), but operates
    # on wrapped objects.
    if space.is_true(space.lt(w_step, space.newint(0))):
        w_start, w_stop = w_stop, w_start
        w_step = space.neg(w_step)
    if space.is_true(space.lt(w_start, w_stop)):
        w_diff = space.sub(space.sub(w_stop, w_start), space.newint(1))
        w_len = space.add(space.floordiv(w_diff, w_step), space.newint(1))
    else:
        w_len = space.newint(0)
    return w_len

def compute_slice_indices3(space, w_slice, w_length):
    "An W_Object version of W_SliceObject.indices3"
    from pypy.objspace.std.sliceobject import W_SliceObject
    assert isinstance(w_slice, W_SliceObject)
    w_0 = space.newint(0)
    w_1 = space.newint(1)
    if space.is_w(w_slice.w_step, space.w_None):
        w_step = w_1
    else:
        w_step = space.index(w_slice.w_step)
        if space.is_true(space.eq(w_step, w_0)):
            raise oefmt(space.w_ValueError, "slice step cannot be zero")
    negative_step = space.is_true(space.lt(w_step, w_0))
    if space.is_w(w_slice.w_start, space.w_None):
        if negative_step:
            w_start = space.sub(w_length, w_1)
        else:
            w_start = w_0
    else:
        w_start = space.index(w_slice.w_start)
        if space.is_true(space.lt(w_start, w_0)):
            w_start = space.add(w_start, w_length)
            if space.is_true(space.lt(w_start, w_0)):
                if negative_step:
                    w_start = space.newint(-1)
                else:
                    w_start = w_0
        elif space.is_true(space.ge(w_start, w_length)):
            if negative_step:
                w_start = space.sub(w_length, w_1)
            else:
                w_start = w_length
    if space.is_w(w_slice.w_stop, space.w_None):
        if negative_step:
            w_stop = space.newint(-1)
        else:
            w_stop = w_length
    else:
        w_stop = space.index(w_slice.w_stop)
        if space.is_true(space.lt(w_stop, w_0)):
            w_stop = space.add(w_stop, w_length)
            if space.is_true(space.lt(w_stop, w_0)):
                if negative_step:
                    w_stop = space.newint(-1)
                else:
                    w_stop = w_0
        elif space.is_true(space.ge(w_stop, w_length)):
            if negative_step:
                w_stop = space.sub(w_length, w_1)
            else:
                w_stop = w_length
    return w_start, w_stop, w_step

def get_printable_location(has_key, has_item, greenkey):
    return "min [has_key=%s, has_item=%s, %s]" % (
            has_key, has_item, greenkey.iterator_greenkey_printable())

min_jitdriver = jit.JitDriver(name='min',
        greens=['has_key', 'has_item', 'greenkey'], reds='auto',
        get_printable_location=get_printable_location)

def get_printable_location(has_key, has_item, greenkey):
    return "min [has_key=%s, has_item=%s, %s]" % (
            has_key, has_item, greenkey.iterator_greenkey_printable())

max_jitdriver = jit.JitDriver(name='max',
        greens=['has_key', 'has_item', 'greenkey'], reds='auto',
        get_printable_location=get_printable_location)

@specialize.arg(4)
def min_max_sequence(space, w_sequence, w_key, w_default, implementation_of):
    if implementation_of == "max":
        compare = space.gt
        jitdriver = max_jitdriver
    else:
        compare = space.lt
        jitdriver = min_jitdriver
    w_iter = space.iter(w_sequence)
    greenkey = space.iterator_greenkey(w_iter)
    has_key = w_key is not None
    has_item = False
    w_max_item = w_default
    w_max_val = None
    while True:
        jitdriver.jit_merge_point(has_key=has_key, has_item=has_item,
                                  greenkey=greenkey)
        try:
            w_item = space.next(w_iter)
        except OperationError as e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        if has_key:
            w_compare_with = space.call_function(w_key, w_item)
        else:
            w_compare_with = w_item
        if (not has_item or
                space.is_true(compare(w_compare_with, w_max_val))):
            has_item = True
            w_max_item = w_item
            w_max_val = w_compare_with
    if not has_item and not w_max_item:
        raise oefmt(space.w_ValueError, "arg is an empty sequence")
    return w_max_item

@specialize.arg(3)
@jit.look_inside_iff(lambda space, args_w, w_key, implementation_of:
        jit.loop_unrolling_heuristic(args_w, len(args_w), 3))
def min_max_multiple_args(space, args_w, w_key, implementation_of):
    # case of multiple arguments (at least two).  We unroll it if there
    # are 2 or 3 arguments.
    if implementation_of == "max":
        compare = space.gt
    else:
        compare = space.lt
    w_max_item = args_w[0]
    if w_key is not None:
        w_max_val = space.call_function(w_key, w_max_item)
    else:
        w_max_val = w_max_item
    for i in range(1, len(args_w)):
        w_item = args_w[i]
        if w_key is not None:
            w_compare_with = space.call_function(w_key, w_item)
        else:
            w_compare_with = w_item
        if space.is_true(compare(w_compare_with, w_max_val)):
            w_max_item = w_item
            w_max_val = w_compare_with
    return w_max_item

@jit.unroll_safe     # the loop over kwds
@specialize.arg(2)
def min_max(space, args, implementation_of):
    w_key = None
    w_default = None
    if bool(args.keyword_names_w):
        kwds_w = args.keyword_names_w
        for n in range(len(kwds_w)):
            if space.eq_w(kwds_w[n], space.newtext("key")):
                w_key = args.keywords_w[n]
            elif space.eq_w(kwds_w[n], space.newtext("default")):
                w_default = args.keywords_w[n]
            else:
                raise oefmt(space.w_TypeError,
                            "%s() got unexpected keyword argument",
                            implementation_of)
    #
    if space.is_w(w_key, space.w_None):
        w_key = None
    args_w = args.arguments_w
    if len(args_w) > 1:
        if w_default is not None:
            raise oefmt(space.w_TypeError,
                "Cannot specify a default for %s() with multiple "
                "positional arguments", implementation_of)
        return min_max_multiple_args(space, args_w, w_key, implementation_of)
    elif len(args_w):
        return min_max_sequence(space, args_w[0], w_key, w_default,
                                implementation_of)
    else:
        raise oefmt(space.w_TypeError,
                    "%s() expected at least one argument, got 0",
                    implementation_of)

def max(space, __args__):
    """max(iterable, *[, default=obj, key=func]) -> value
max(arg1, arg2, *args, *[, key=func]) -> value

With a single iterable argument, return its biggest item. The
default keyword-only argument specifies an object to return if
the provided iterable is empty.
With two or more arguments, return the largest argument.
    """
    return min_max(space, __args__, "max")

def min(space, __args__):
    """min(iterable, *[, default=obj, key=func]) -> value
min(arg1, arg2, *args, *[, key=func]) -> value

With a single iterable argument, return its smallest item. The
default keyword-only argument specifies an object to return if
the provided iterable is empty.
With two or more arguments, return the smallest argument.
    """
    return min_max(space, __args__, "min")



class W_Enumerate(W_Root):
    def __init__(self, w_iter_or_list, start, w_start):
        # 'w_index' should never be a wrapped int here; if it would be,
        # then it is actually None and the unwrapped int is in 'index'.
        self.w_iter_or_list = w_iter_or_list
        self.index = start
        self.w_index = w_start

    @staticmethod
    def descr___new__(space, w_subtype, w_iterable, w_start=None):
        from pypy.objspace.std.listobject import W_ListObject

        if w_start is None:
            start = 0
        else:
            w_start = space.index(w_start)
            try:
                start = space.int_w(w_start)
                w_start = None
            except OperationError as e:
                if not e.match(space, space.w_OverflowError):
                    raise
                start = -1

        if start == 0 and type(w_iterable) is W_ListObject:
            w_iter = w_iterable
        else:
            w_iter = space.iter(w_iterable)

        self = space.allocate_instance(W_Enumerate, w_subtype)
        self.__init__(w_iter, start, w_start)
        return self

    def descr___iter__(self, space):
        return self

    def descr_next(self, space):
        from pypy.objspace.std.listobject import W_ListObject
        w_index = self.w_index
        w_iter_or_list = self.w_iter_or_list
        w_item = None
        if w_index is None:
            index = self.index
            if type(w_iter_or_list) is W_ListObject:
                try:
                    w_item = w_iter_or_list.getitem(index)
                except IndexError:
                    self.w_iter_or_list = None
                    raise OperationError(space.w_StopIteration, space.w_None)
                self.index = index + 1
            elif w_iter_or_list is None:
                raise OperationError(space.w_StopIteration, space.w_None)
            else:
                try:
                    newval = rarithmetic.ovfcheck(index + 1)
                except OverflowError:
                    w_index = space.newint(index)
                    self.w_index = space.add(w_index, space.newint(1))
                    self.index = -1
                else:
                    self.index = newval
            w_index = space.newint(index)
        else:
            self.w_index = space.add(w_index, space.newint(1))
        if w_item is None:
            w_item = space.next(self.w_iter_or_list)
        return space.newtuple2(w_index, w_item)

    def descr___reduce__(self, space):
        w_index = self.w_index
        if w_index is None:
            w_index = space.newint(self.index)
        return space.newtuple2(space.type(self),
                               space.newtuple2(self.w_iter_or_list, w_index))

# exported through _pickle_support
def _make_enumerate(space, w_iter_or_list, w_index):
    if space.is_w(space.type(w_index), space.w_int):
        index = space.int_w(w_index)
        w_index = None
    else:
        index = -1
    return W_Enumerate(w_iter_or_list, index, w_index)

W_Enumerate.typedef = TypeDef("enumerate",
    __doc__           = """\
Return an enumerate object.

  iterable
    an object supporting iteration

The enumerate object yields pairs containing a count (from start, which
defaults to zero) and a value yielded by the iterable argument.

enumerate is useful for obtaining an indexed list:
    (0, seq[0]), (1, seq[1]), (2, seq[2]), ...""",

    _text_signature_  = "(iterable, start=0)",
    __new__           = interp2app(W_Enumerate.descr___new__),
    __iter__          = interp2app(W_Enumerate.descr___iter__),
    __next__          = interp2app(W_Enumerate.descr_next),
    __reduce__        = interp2app(W_Enumerate.descr___reduce__),
    __class_getitem__ = interp2app(
        generic_alias_class_getitem, as_classmethod=True),
)


class W_ReversedIterator(W_Root):
    """reverse iterator over values of the sequence."""

    def __init__(self, space, w_sequence):
        self.remaining = space.len_w(w_sequence) - 1
        if not space.issequence_w(w_sequence):
            raise oefmt(space.w_TypeError,
                        "argument to reversed() must be a sequence")
        self.w_sequence = w_sequence

    @staticmethod
    def descr___new__2(space, w_subtype, w_sequence):
        w_reversed_descr = space.lookup(w_sequence, "__reversed__")
        if w_reversed_descr is not None:
            w_reversed = space.get(w_reversed_descr, w_sequence)
            return space.call_function(w_reversed)
        self = space.allocate_instance(W_ReversedIterator, w_subtype)
        self.__init__(space, w_sequence)
        return self

    def descr___iter__(self, space):
        return self

    def descr_length_hint(self, space):
        # bah, there is even a CPython test that checks that this
        # actually calls 'len_w(w_sequence)'.  Obscure.
        res = 0
        if self.remaining >= 0:
            total_length = space.len_w(self.w_sequence)
            rem_length = self.remaining + 1
            if rem_length <= total_length:
                res = rem_length
        return space.newint(res)

    def descr_next(self, space):
        if self.remaining >= 0:
            w_index = space.newint(self.remaining)
            try:
                w_item = space.getitem(self.w_sequence, w_index)
            except OperationError as e:
                # Done
                self.remaining = -1
                self.w_sequence = None
                if not (e.match(space, space.w_IndexError) or
                        e.match(space, space.w_StopIteration)):
                    raise
                raise OperationError(space.w_StopIteration, space.w_None)
            else:
                self.remaining -= 1
                return w_item

        # Done
        self.remaining = -1
        self.w_sequence = None
        raise OperationError(space.w_StopIteration, space.w_None)

    def descr___reduce__(self, space):
        if self.w_sequence:
            w_state = space.newint(self.remaining)
            return space.newtuple([
                space.type(self),
                space.newtuple([self.w_sequence]),
                w_state])
        else:
            return space.newtuple2(
                space.type(self),
                space.newtuple([space.newtuple([])]))

    def descr___setstate__(self, space, w_state):
        self.remaining = space.int_w(w_state)
        n = space.len_w(self.w_sequence)
        if self.remaining < -1:
            self.remaining = -1
        elif self.remaining > n - 1:
            self.remaining = n - 1

W_ReversedIterator.typedef = TypeDef("reversed",
    __doc__         = """\
Return a reverse iterator over the values of the given sequence.""",
    _text_signature_ = "(sequence, /)",
    __new__         = interp2app(W_ReversedIterator.descr___new__2),
    __iter__        = interp2app(W_ReversedIterator.descr___iter__),
    __length_hint__ = interp2app(W_ReversedIterator.descr_length_hint),
    __next__        = interp2app(W_ReversedIterator.descr_next),
    __reduce__      = interp2app(W_ReversedIterator.descr___reduce__),
    __setstate__      = interp2app(W_ReversedIterator.descr___setstate__),
)


class W_Range(W_Root):
    def __init__(self, w_start, w_stop, w_step, w_length, promote_step=False):
        self.w_start = w_start
        self.w_stop  = w_stop
        self.w_step  = w_step
        self.w_length = w_length
        self.promote_step = promote_step

    def descr_new(space, w_subtype, w_start, w_stop=None, w_step=None):
        w_start = space.index(w_start)
        promote_step = False
        if space.is_none(w_step):  # no step argument provided
            w_step = space.newint(1)
            promote_step = True
        if space.is_none(w_stop):  # only 1 argument provided
            w_start, w_stop = space.newint(0), w_start
        else:
            w_stop = space.index(w_stop)
            w_step = space.index(w_step)
        try:
            step = space.int_w(w_step)
        except OperationError:
            pass  # We know it's not zero
        else:
            if step == 0:
                raise oefmt(space.w_ValueError,
                            "step argument must not be zero")
        w_length = compute_range_length(space, w_start, w_stop, w_step)
        obj = space.allocate_instance(W_Range, w_subtype)
        W_Range.__init__(obj, w_start, w_stop, w_step, w_length, promote_step)
        return obj

    def descr_repr(self, space):
        if not space.is_true(space.eq(self.w_step, space.newint(1))):
            return space.mod(space.newtext("range(%d, %d, %d)"),
                             space.newtuple([self.w_start, self.w_stop,
                                             self.w_step]))
        else:
            return space.mod(space.newtext("range(%d, %d)"),
                             space.newtuple([self.w_start, self.w_stop]))

    def descr_len(self):
        return self.w_length

    def _compute_item0(self, space, w_index):
        "Get a range item, when known to be inside bounds"
        # return self.start + (i * self.step)
        return space.add(self.w_start, space.mul(w_index, self.w_step))

    def _compute_item(self, space, w_index):
        w_zero = space.newint(0)
        w_index = space.index(w_index)
        if space.is_true(space.lt(w_index, w_zero)):
            w_index = space.add(w_index, self.w_length)
        if (space.is_true(space.ge(w_index, self.w_length)) or
            space.is_true(space.lt(w_index, w_zero))):
            raise oefmt(space.w_IndexError, "range object index out of range")
        return self._compute_item0(space, w_index)

    def _compute_slice(self, space, w_slice):
        w_start, w_stop, w_step = compute_slice_indices3(
            space, w_slice, self.w_length)

        w_substep = space.mul(self.w_step, w_step)
        w_substart = self._compute_item0(space, w_start)
        if w_stop:
            w_substop = self._compute_item0(space, w_stop)
        else:
            w_substop = w_substart

        w_length = compute_range_length(space, w_substart, w_substop, w_substep)
        obj = W_Range(w_substart, w_substop, w_substep, w_length)
        return obj

    def descr_getitem(self, space, w_index):
        # Cannot use the usual space.decode_index methods, because
        # numbers might not fit in longs.
        if space.isinstance_w(w_index, space.w_slice):
            return self._compute_slice(space, w_index)
        else:
            return self._compute_item(space, w_index)

    def descr_iter(self, space):
        try:
            start = space.int_w(self.w_start)
            stop = space.int_w(self.w_stop)
            step = space.int_w(self.w_step)
            length = space.int_w(self.w_length)
        except OperationError as e:
            pass
        else:
            if self.promote_step:
                if start == 0:
                    return W_IntRangeOneArgIterator(space, stop)
                return W_IntRangeStepOneIterator(space, start, stop)
            return W_IntRangeIterator(space, start, length, step)
        return W_LongRangeIterator(space, self.w_start, self.w_step,
                                   self.w_length)

    def descr_reversed(self, space):
        # lastitem = self.start + (self.length-1) * self.step
        w_lastitem = space.add(
            self.w_start,
            space.mul(space.sub(self.w_length, space.newint(1)),
                      self.w_step))
        return W_LongRangeIterator(
                space, w_lastitem, space.neg(self.w_step), self.w_length)

    def descr_reduce(self, space):
        return space.newtuple(
            [space.type(self),
             space.newtuple([self.w_start, self.w_stop, self.w_step]),
             ])

    def _contains_long(self, space, w_item):
        # Check if the value can possibly be in the range.
        if space.is_true(space.gt(self.w_step, space.newint(0))):
            # positive steps: start <= ob < stop
            if not (space.is_true(space.le(self.w_start, w_item)) and
                    space.is_true(space.lt(w_item, self.w_stop))):
                return False
        else:
            # negative steps: stop < ob <= start
            if not (space.is_true(space.lt(self.w_stop, w_item)) and
                    space.is_true(space.le(w_item, self.w_start))):
                return False
        # Check that the stride does not invalidate ob's membership.
        if space.is_true(space.mod(space.sub(w_item, self.w_start),
                                   self.w_step)):
            return False
        return True

    def descr_contains(self, space, w_item):
        w_type = space.type(w_item)
        if space.is_w(w_type, space.w_int) or space.is_w(w_type, space.w_bool):
            return space.newbool(self._contains_long(space, w_item))
        else:
            return space.sequence_contains(self, w_item)

    def descr_count(self, space, w_item):
        w_type = space.type(w_item)
        if space.is_w(w_type, space.w_int) or space.is_w(w_type, space.w_bool):
            return space.newint(self._contains_long(space, w_item))
        else:
            return space.sequence_count(self, w_item)

    def descr_index(self, space, w_item):
        w_type = space.type(w_item)
        if not (space.is_w(w_type, space.w_int) or
                space.is_w(w_type, space.w_bool)):
            return space.sequence_index(self, w_item)

        if not self._contains_long(space, w_item):
            raise oefmt(space.w_ValueError, "%R is not in range", w_item)
        w_index = space.sub(w_item, self.w_start)
        return space.floordiv(w_index, self.w_step)

    def descr_eq(self, space, w_other):
        # Compare two range objects.
        if space.is_w(self, w_other):
            return space.w_True
        if not isinstance(w_other, W_Range):
            return space.w_NotImplemented
        if not space.eq_w(self.w_length, w_other.w_length):
            return space.w_False
        if space.eq_w(self.w_length, space.newint(0)):
            return space.w_True
        if not space.eq_w(self.w_start, w_other.w_start):
            return space.w_False
        if space.eq_w(self.w_length, space.newint(1)):
            return space.w_True
        return space.eq(self.w_step, w_other.w_step)

    def descr_hash(self, space):
        if space.eq_w(self.w_length, space.newint(0)):
            w_tup = space.newtuple([self.w_length, space.w_None, space.w_None])
        elif space.eq_w(self.w_length, space.newint(1)):
            w_tup = space.newtuple([self.w_length, self.w_start, space.w_None])
        else:
            w_tup = space.newtuple([self.w_length, self.w_start, self.w_step])
        return space.hash(w_tup)

    def descr_bool(self, space):
        return space.nonzero(self.w_length)

W_Range.typedef = TypeDef("range",
    __doc__          = """range(stop) -> range object
range(start, stop[, step]) -> range object

Return an object that produces a sequence of integers from start (inclusive)
to stop (exclusive) by step.  range(i, j) produces i, i+1, i+2, ..., j-1.
start defaults to 0, and stop is omitted!  range(4) produces 0, 1, 2, 3.
These are exactly the valid indices for a list of 4 elements.
When step is given, it specifies the increment (or decrement).""",
    __new__          = interp2app(W_Range.descr_new.im_func),
    __repr__         = interp2app(W_Range.descr_repr),
    __getitem__      = interp2app(W_Range.descr_getitem),
    __iter__         = interp2app(W_Range.descr_iter),
    __len__          = interp2app(W_Range.descr_len),
    __reversed__     = interp2app(W_Range.descr_reversed),
    __reduce__       = interp2app(W_Range.descr_reduce),
    __contains__     = interp2app(W_Range.descr_contains),
    __eq__           = interp2app(W_Range.descr_eq),
    __hash__         = interp2app(W_Range.descr_hash),
    __bool__         = interp2app(W_Range.descr_bool),
    count            = interp2app(W_Range.descr_count),
    index            = interp2app(W_Range.descr_index),
    start            = interp_attrproperty_w('w_start', cls=W_Range),
    stop             = interp_attrproperty_w('w_stop', cls=W_Range),
    step             = interp_attrproperty_w('w_step', cls=W_Range),
)
W_Range.typedef.acceptable_as_base_class = False


class W_AbstractRangeIterator(W_Root):

    def descr_iter(self, space):
        return self

    def descr_len(self, space):
        raise NotImplementedError

    def descr_next(self, space):
        raise NotImplementedError

    def descr_reduce(self, space):
        raise NotImplementedError

    def descr_setstate(self, space, w_index):
        raise NotImplementedError

class W_LongRangeIterator(W_AbstractRangeIterator):
    def __init__(self, space, w_start, w_step, w_len, w_index=None):
        self.w_start = w_start
        self.w_step = w_step
        self.w_len = w_len
        if w_index is None:
            w_index = space.newint(0)
        self.w_index = w_index

    def descr_next(self, space):
        if space.is_true(space.lt(self.w_index, self.w_len)):
            w_index = space.add(self.w_index, space.newint(1))
            w_product = space.mul(self.w_index, self.w_step)
            w_result = space.add(w_product, self.w_start)
            self.w_index = w_index
            return w_result
        raise OperationError(space.w_StopIteration, space.w_None)

    def descr_len(self, space):
        return space.sub(self.w_len, self.w_index)

    def descr_reduce(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
        w_args = space.newtuple([self.w_start, self.w_step, self.w_len, self.w_index])
        return space.newtuple([mod.get('longrangeiter_new'), w_args, self.w_index])

    def descr_setstate(self, space, w_index):
        if space.is_true(space.lt(w_index, space.newint(0))):
            w_index = space.newint(0)
        elif space.is_true(space.lt(self.w_len, w_index)):
            w_index = self.w_len
        self.w_index = w_index

class W_IntRangeIterator(W_AbstractRangeIterator):

    def __init__(self, space, current, remaining, step):
        self.start = current
        self.current = current
        self.remaining = remaining
        self.step = step

    def descr_next(self, space):
        return self.next(space)

    def next(self, space):
        if self.remaining > 0:
            item = self.current
            self.current = item + self.step
            self.remaining -= 1
            return space.newint(item)
        raise OperationError(space.w_StopIteration, space.w_None)

    def descr_len(self, space):
        return self.get_remaining(space)

    def descr_reduce(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('intrangeiter_new')
        nt = space.newtuple

        tup = [space.newint(self.current), self.get_remaining(space), space.newint(self.step)]
        return nt([new_inst, nt(tup), self.get_remaining(space)])

    def get_remaining(self, space):
        return space.newint(self.remaining)

    def descr_setstate(self, space, w_remaining):
        remaining = space.int_w(w_remaining)
        if remaining < 0:
            remaining = 0
        if remaining > self.remaining:
            remaining = self.remaining
        self.remaining = remaining


class W_IntRangeStepOneIterator(W_IntRangeIterator):
    _immutable_fields_ = ['stop']

    def __init__(self, space, start, stop):
        self.start = start
        self.current = start
        self.stop = stop
        self.step = 1

    def next(self, space):
        if self.current < self.stop:
            item = self.current
            self.current = item + 1
            return space.newint(item)
        raise OperationError(space.w_StopIteration, space.w_None)

    def get_remaining(self, space):
        return space.newint(self.stop - self.current)

    def descr_setstate(self, space, w_index):
        index = space.int_w(w_index)
        if index < self.start:
            index = self.start 
        elif index > self.stop:
            index = self.stop
        self.current = index


class W_IntRangeOneArgIterator(W_IntRangeIterator):
    """ iterator for range(integer). useful because the jit knows that its
    values are always >= 0 """

    _immutable_fields_ = ['stop']

    def __init__(self, space, stop):
        self.current = 0
        self.stop = stop
        self.step = 1

    def next(self, space):
        current = self.current
        assert current >= 0
        if current < self.stop:
            self.current = current + 1
            return space.newint(current)
        raise OperationError(space.w_StopIteration, space.w_None)

    def get_remaining(self, space):
        return space.newint(self.stop - self.current)

    def descr_setstate(self, space, w_index):
        index = space.int_w(w_index)
        if index < 0:
            index = 0
        elif index > self.stop:
            index = self.stop
        self.current = index

W_AbstractRangeIterator.typedef = TypeDef("range_iterator",
    __iter__        = interp2app(W_AbstractRangeIterator.descr_iter),
    __length_hint__ = interpindirect2app(W_AbstractRangeIterator.descr_len),
    __next__        = interpindirect2app(W_AbstractRangeIterator.descr_next),
    __reduce__      = interpindirect2app(W_AbstractRangeIterator.descr_reduce),
    __setstate__    = interpindirect2app(W_AbstractRangeIterator.descr_setstate),
)
W_AbstractRangeIterator.typedef.acceptable_as_base_class = False


@jit.look_inside_iff(lambda space, args_w, error_name:
        jit.isconstant(len(args_w)) and len(args_w) <= 2)
def build_iterators_from_args(space, args_w, error_name):
    iterators_w = []
    i = 0
    for iterable_w in args_w:
        try:
            iterator_w = space.iter(iterable_w)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise oefmt(space.w_TypeError,
                            "%s argument #%d must support iteration",
                            error_name, i + 1)
            else:
                raise
        else:
            iterators_w.append(iterator_w)

        i += 1
    return iterators_w

class W_Map(W_Root):
    _immutable_fields_ = ["w_fun", "iterators_w"]

    def __init__(self, space, w_fun, args_w):
        self.space = space
        self.w_fun = w_fun
        self.iterators_w = build_iterators_from_args(space, args_w, "map")

    def iter_w(self):
        return self

    def next_w(self):
        # common case: 1 or 2 arguments
        iterators_w = self.iterators_w
        length = len(iterators_w)
        if length == 1:
            w_a = self.space.next(iterators_w[0])
            return self.space.call_function(self.w_fun, w_a)
        elif length == 2:
            w_a = self.space.next(iterators_w[0])
            w_b = self.space.next(iterators_w[1])
            return self.space.call_function(self.w_fun, w_a, w_b)
        else:
            objects = self._get_objects()
            w_objects = self.space.newtuple(objects)
            return self.space.call(self.w_fun, w_objects)

    def _get_objects(self):
        # the loop is out of the way of the JIT
        return [self.space.next(w_elem) for w_elem in self.iterators_w]

    def descr_reduce(self, space):
        w_map = space.getattr(space.getbuiltinmodule('builtins'),
                space.newtext('map'))
        args_w = [self.w_fun] + self.iterators_w
        return space.newtuple([w_map, space.newtuple(args_w)])

    def iterator_greenkey(self, space):
        # XXX in theory we should tupleize the greenkeys of the callable and
        # the sub-iterators, but much more work
        if self.w_fun is not None:
            w_res = space._try_fetch_pycode(self.w_fun)
            if w_res is None:
                w_res = self.space.type(self.w_fun)
        elif len(self.iterators_w) > 0:
            w_res = space.iterator_greenkey(self.iterators_w[0])
        else:
            w_res = None
        return w_res

def W_Map___new__(space, w_subtype, w_fun, args_w):
    if len(args_w) == 0:
        raise oefmt(space.w_TypeError,
                    "map() must have at least two arguments")
    r = space.allocate_instance(W_Map, w_subtype)
    r.__init__(space, w_fun, args_w)
    return r

W_Map.typedef = TypeDef(
        'map',
        __new__  = interp2app(W_Map___new__),
        __iter__ = interp2app(W_Map.iter_w),
        __next__ = interp2app(W_Map.next_w),
        __reduce__ = interp2app(W_Map.descr_reduce),
        __doc__ = """\
map(func, *iterables) --> map object

Make an iterator that computes the function using arguments from
each of the iterables.  Stops when the shortest iterable is exhausted.""")

class W_Filter(W_Root):
    reverse = False # set to True in itertools

    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        if space.is_w(w_predicate, space.w_None):
            self.w_predicate = None
        else:
            self.w_predicate = w_predicate
        self.w_iterable = space.iter(w_iterable)

    def iter_w(self):
        return self

    def next_w(self):
        # unroll one iteration in case the filter mostly returns true
        w_obj = self.space.next(self.w_iterable)  # may raise w_StopIteration
        if self.w_predicate is None:
            pred = self.space.is_true(w_obj)
        else:
            w_pred = self.space.call_function(self.w_predicate, w_obj)
            pred = self.space.is_true(w_pred)
        if pred ^ self.reverse:
            return w_obj
        # otherwise, use a jit driver
        return _filter_jitdriver(self.space, self.w_iterable,
                self.w_predicate, self.reverse)

    def descr_reduce(self, space):
        w_filter = space.getattr(space.getbuiltinmodule('builtins'),
                space.newtext('filter'))
        args_w = [space.w_None if self.w_predicate is None else self.w_predicate,
                  self.w_iterable]
        return space.newtuple([w_filter, space.newtuple(args_w)])

def get_printable_location(reverse, likely_pycode, greenkey):
    return "filter [reverse=%s, %s]" % (
            reverse, greenkey.iterator_greenkey_printable())

filter_jitdriver = jit.JitDriver(name='filter',
        greens=['reverse', 'callable_greenkey', 'greenkey'], reds='auto',
        get_printable_location=get_printable_location)

def _filter_jitdriver(space, w_iterable, w_predicate, reverse):
    callable_greenkey = None
    if w_predicate is not None:
        callable_greenkey = space._try_fetch_pycode(w_predicate)
        if callable_greenkey is None:
            callable_greenkey = space.type(w_predicate)
    greenkey = space.iterator_greenkey(w_iterable)
    while True:
        filter_jitdriver.jit_merge_point(
                reverse=reverse,
                callable_greenkey=callable_greenkey,
                greenkey=greenkey)
        w_obj = space.next(w_iterable)  # may raise w_StopIteration
        if w_predicate is None:
            pred = space.is_true(w_obj)
        else:
            w_pred = space.call_function(w_predicate, w_obj)
            pred = space.is_true(w_pred)
        if pred ^ reverse:
            return w_obj

def W_Filter___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_Filter, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return r

W_Filter.typedef = TypeDef(
        'filter',
        __new__  = interp2app(W_Filter___new__),
        __iter__ = interp2app(W_Filter.iter_w),
        __next__ = interp2app(W_Filter.next_w),
        __reduce__ = interp2app(W_Filter.descr_reduce),
        __doc__  = """\
filter(function or None, iterable) --> filter object

Return an iterator yielding those items of iterable for which function(item)
is true. If function is None, return the items that are true.""")


class W_Zip(W_Root):
    _immutable_fields_ = ["w_fun", "iterators_w", "strict"]

    def __init__(self, space, args_w, strict=False):
        self.strict = strict
        self.space = space
        self.iterators_w = build_iterators_from_args(space, args_w, "zip")
        self._iteration_progress = 0

    def iter_w(self):
        return self

    def next_w(self):
        iterators_w = self.iterators_w
        length = len(iterators_w)
        if length == 0:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        if length == 1:
            return self.space.newtuple([self.space.next(iterators_w[0])])

        try:
            self._iteration_progress = 0
            objects = None
            if length == 2:
                w_a = self.space.next(iterators_w[0])
                self._iteration_progress = 1
                w_b = self.space.next(iterators_w[1])
                return self.space.newtuple2(w_a, w_b)
            else:
                objects = [None] * length
                self._get_objects(objects)
                return self.space.newtuple(objects)
        except OperationError as e:
            if not e.match(self.space, self.space.w_StopIteration) or not self.strict:
                raise
            if self._iteration_progress:
                self._raise_strict_error(self._iteration_progress, "shorter")
            elif length == 2:
                try:
                    self.space.next(iterators_w[1])
                except OperationError as e:
                    if not e.match(self.space, self.space.w_StopIteration):
                        raise
                else:
                    self._raise_strict_error(1, "longer")
            else:
                self._validate_strict(objects)
            raise e

    def _get_objects(self, objects):
        # the loop is out of the way of the JIT
        for i, w_elem in enumerate(self.iterators_w):
            objects[i] = self.space.next(w_elem)
            self._iteration_progress += 1

    def _raise_strict_error(self, index, adjective):
        plural = " " if index == 1 else "s 1-"
        raise oefmt(self.space.w_ValueError, "zip() argument %d is %s than argument%s%d", index+1, adjective, plural, index)

    def _validate_strict(self, objects):
        # keep validation in its own function so the loop doesn't prevent the
        # JIT from inlining W_Zip.next_w
        for i, w_elem in enumerate(self.iterators_w):
            try:
                self.space.next(w_elem)
            except OperationError as e:
                if not e.match(self.space, self.space.w_StopIteration):
                    raise
            else:
                self._raise_strict_error(i, "longer")

    def descr_reduce(self, space):
        w_zip = space.getattr(space.getbuiltinmodule('builtins'),
                space.newtext('zip'))
        w_iterators = space.newtuple(self.iterators_w)
        if self.strict:
            return space.newtuple([w_zip, w_iterators, space.w_True])
        return space.newtuple2(w_zip, w_iterators)

    def descr_setstate(self, space, w_state):
        strict = space.bool_w(w_state)
        self.strict = strict

    def iterator_greenkey(self, space):
        # XXX in theory we should tupleize the greenkeys of all the
        # sub-iterators, but much more work
        if len(self.iterators_w) > 0:
            return space.iterator_greenkey(self.iterators_w[0])
        return None


@unwrap_spec(strict=bool)
def W_Zip___new__(space, w_subtype, args_w, __kwonly__, strict=False):
    r = space.allocate_instance(W_Zip, w_subtype)
    r.__init__(space, args_w, strict)
    return r

W_Zip.typedef = TypeDef(
        'zip',
        __new__  = interp2app(W_Zip___new__),
        __iter__ = interp2app(W_Zip.iter_w),
        __next__ = interp2app(W_Zip.next_w),
        __reduce__ = interp2app(W_Zip.descr_reduce),
        __setstate__ = interp2app(W_Zip.descr_setstate),
        __doc__  = """\
zip(*iterables) --> A zip object yielding tuples until an input is exhausted.

   >>> list(zip('abcdefg', range(3), range(4)))
   [('a', 0, 0), ('b', 1, 1), ('c', 2, 2)]

The zip object yields n-length tuples, where n is the number of iterables
passed as positional arguments to zip().  The i-th element in every tuple
comes from the i-th iterable argument to zip().  This continues until the
shortest argument is exhausted.""")
