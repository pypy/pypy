"""
Interp-level definition of frequently used functionals.

"""
import sys

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.typedef import TypeDef
from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_uint, intmask


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
            raise OperationError(space.w_ValueError,
                                 space.wrap("slice step cannot be zero"))
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
    
min_jitdriver = jit.JitDriver(name='min',
        greens=['has_key', 'has_item', 'w_type'], reds='auto')
max_jitdriver = jit.JitDriver(name='max',
        greens=['has_key', 'has_item', 'w_type'], reds='auto')

def make_min_max(unroll):
    @specialize.arg(2)
    def min_max_impl(space, args, implementation_of):
        if implementation_of == "max":
            compare = space.gt
            jitdriver = max_jitdriver
        else:
            compare = space.lt
            jitdriver = min_jitdriver
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
        w_type = space.type(w_iter)
        has_key = w_key is not None
        has_item = False
        w_max_item = None
        w_max_val = None
        while True:
            if not unroll:
                jitdriver.jit_merge_point(has_key=has_key, has_item=has_item, w_type=w_type)
            try:
                w_item = space.next(w_iter)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break
            if has_key:
                w_compare_with = space.call_function(w_key, w_item)
            else:
                w_compare_with = w_item
            if not has_item or \
                    space.is_true(compare(w_compare_with, w_max_val)):
                has_item = True
                w_max_item = w_item
                w_max_val = w_compare_with
        if w_max_item is None:
            msg = "arg is an empty sequence"
            raise OperationError(space.w_ValueError, space.wrap(msg))
        return w_max_item
    if unroll:
        min_max_impl = jit.unroll_safe(min_max_impl)
    return min_max_impl

min_max_unroll = make_min_max(True)
min_max_normal = make_min_max(False)

@specialize.arg(2)
def min_max(space, args, implementation_of):
    if not jit.we_are_jitted() or len(args.arguments_w) != 1 and \
            jit.loop_unrolling_heuristic(args.arguments_w, len(args.arguments_w)):
        return min_max_unroll(space, args, implementation_of)
    else:
        return min_max_normal(space, args, implementation_of)
min_max._always_inline = True

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


class W_Enumerate(W_Root):
    def __init__(self, w_iter, w_start):
        self.w_iter = w_iter
        self.w_index = w_start

    def descr___new__(space, w_subtype, w_iterable, w_start=None):
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
    __next__=interp2app(W_Enumerate.descr_next),
    __reduce__=interp2app(W_Enumerate.descr___reduce__),
)


def reversed(space, w_sequence):
    """Return a iterator that yields items of sequence in reverse."""
    w_reversed_descr = space.lookup(w_sequence, "__reversed__")
    if w_reversed_descr is not None:
        w_reversed = space.get(w_reversed_descr, w_sequence)
        return space.call_function(w_reversed)
    return space.wrap(W_ReversedIterator(space, w_sequence))


class W_ReversedIterator(W_Root):
    def __init__(self, space, w_sequence):
        self.remaining = space.len_w(w_sequence) - 1
        if space.lookup(w_sequence, "__getitem__") is None:
            msg = "reversed() argument must be a sequence"
            raise OperationError(space.w_TypeError, space.wrap(msg))
        self.w_sequence = w_sequence

    def descr___iter__(self, space):
        return space.wrap(self)

    def descr_length(self, space):
        return space.wrap(0 if self.remaining == -1 else self.remaining + 1)

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
    __iter__        = interp2app(W_ReversedIterator.descr___iter__),
    __length_hint__ = interp2app(W_ReversedIterator.descr_length),
    __next__        = interp2app(W_ReversedIterator.descr_next),
    __reduce__      = interp2app(W_ReversedIterator.descr___reduce__),
)
W_ReversedIterator.typedef.acceptable_as_base_class = False

# exported through _pickle_support
def _make_reversed(space, w_seq, w_remaining):
    w_type = space.gettypeobject(W_ReversedIterator.typedef)
    iterator = space.allocate_instance(W_ReversedIterator, w_type)
    iterator.w_sequence = w_seq
    iterator.remaining = space.int_w(w_remaining)
    return space.wrap(iterator)



class W_Range(W_Root):
    def __init__(self, w_start, w_stop, w_step, w_length):
        self.w_start = w_start
        self.w_stop  = w_stop
        self.w_step  = w_step
        self.w_length = w_length

    @unwrap_spec(w_step = WrappedDefault(1))
    def descr_new(space, w_subtype, w_start, w_stop=None, w_step=None):
        w_start = space.index(w_start)
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
                raise OperationError(space.w_ValueError, space.wrap(
                        "step argument must not be zero"))
        w_length = compute_range_length(space, w_start, w_stop, w_step)
        obj = space.allocate_instance(W_Range, w_subtype)
        W_Range.__init__(obj, w_start, w_stop, w_step, w_length)
        return space.wrap(obj)

    def descr_repr(self, space):
        if not space.is_true(space.eq(self.w_step, space.newint(1))):
            return space.mod(space.wrap("range(%d, %d, %d)"),
                             space.newtuple([self.w_start, self.w_stop, 
                                             self.w_step]))
        else:
            return space.mod(space.wrap("range(%d, %d)"),
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
            raise OperationError(space.w_IndexError, space.wrap(
                    "range object index out of range"))
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
        return space.wrap(obj)

    def descr_getitem(self, space, w_index):
        # Cannot use the usual space.decode_index methods, because
        # numbers might not fit in longs.
        if space.isinstance_w(w_index, space.w_slice):
            return self._compute_slice(space, w_index)
        else:
            return self._compute_item(space, w_index)

    def descr_iter(self, space):
        return space.wrap(W_RangeIterator(
                space, self.w_start, self.w_step, self.w_length))

    def descr_reversed(self, space):
        # lastitem = self.start + (self.length-1) * self.step
        w_lastitem = space.add(
            self.w_start,
            space.mul(space.sub(self.w_length, space.newint(1)),
                      self.w_step))
        return space.wrap(W_RangeIterator(
                space, w_lastitem, space.neg(self.w_step), self.w_length))

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


W_Range.typedef = TypeDef("range",
    __new__          = interp2app(W_Range.descr_new.im_func),
    __repr__         = interp2app(W_Range.descr_repr),
    __getitem__      = interp2app(W_Range.descr_getitem),
    __iter__         = interp2app(W_Range.descr_iter),
    __len__          = interp2app(W_Range.descr_len),
    __reversed__     = interp2app(W_Range.descr_reversed),
    __reduce__       = interp2app(W_Range.descr_reduce),
    __contains__     = interp2app(W_Range.descr_contains),
    count            = interp2app(W_Range.descr_count),
    index            = interp2app(W_Range.descr_index),
)
W_Range.typedef.acceptable_as_base_class = False

class W_RangeIterator(W_Root):
    def __init__(self, space, w_start, w_step, w_len, w_index=None):
        self.w_start = w_start
        self.w_step = w_step
        self.w_len = w_len
        if w_index is None:
            w_index = space.newint(0)
        self.w_index = w_index

    def descr_iter(self, space):
        return space.wrap(self)

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
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)

        return space.newtuple(
            [mod.get('rangeiter_new'),
             space.newtuple([self.w_start, self.w_step,
                             self.w_len, self.w_index]),
             ])


W_RangeIterator.typedef = TypeDef("rangeiterator",
    __iter__        = interp2app(W_RangeIterator.descr_iter),
    __length_hint__ = interp2app(W_RangeIterator.descr_len),
    __next__        = interp2app(W_RangeIterator.descr_next),
    __reduce__      = interp2app(W_RangeIterator.descr_reduce),
)
W_RangeIterator.typedef.acceptable_as_base_class = False


class W_Map(W_Root):
    _error_name = "map"
    _immutable_fields_ = ["w_fun", "iterators_w"]

    def __init__(self, space, w_fun, args_w):
        self.space = space
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


def W_Map___new__(space, w_subtype, w_fun, args_w):
    if len(args_w) == 0:
        raise OperationError(space.w_TypeError,
                  space.wrap("map() must have at least two arguments"))
    r = space.allocate_instance(W_Map, w_subtype)
    r.__init__(space, w_fun, args_w)
    return space.wrap(r)

W_Map.typedef = TypeDef(
        'map',
        __new__  = interp2app(W_Map___new__),
        __iter__ = interp2app(W_Map.iter_w),
        __next__ = interp2app(W_Map.next_w),
        __doc__ = """\ 
Make an iterator that computes the function using arguments from
each of the iterables.  Stops when the shortest iterable is exhausted.""")

class W_Filter(W_Root):
    reverse = False

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


def W_Filter___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_Filter, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return space.wrap(r)

W_Filter.typedef = TypeDef(
        'filter',
        __new__  = interp2app(W_Filter___new__),
        __iter__ = interp2app(W_Filter.iter_w),
        __next__ = interp2app(W_Filter.next_w),
        __doc__  = """\
Return an iterator yielding those items of iterable for which function(item)
is true. If function is None, return the items that are true.""")


class W_Zip(W_Map):
    _error_name = "zip"

    def next_w(self):
        # argh.  zip(*args) is almost like map(None, *args) except
        # that the former needs a special case for len(args)==0
        # while the latter just raises a TypeError in this situation.
        if len(self.iterators_w) == 0:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        return W_Map.next_w(self)

def W_Zip___new__(space, w_subtype, args_w):
    r = space.allocate_instance(W_Zip, w_subtype)
    r.__init__(space, None, args_w)
    return space.wrap(r)

W_Zip.typedef = TypeDef(
        'zip',
        __new__  = interp2app(W_Zip___new__),
        __iter__ = interp2app(W_Zip.iter_w),
        __next__ = interp2app(W_Zip.next_w),
        __doc__  = """\
Return a zip object whose .__next__() method returns a tuple where
the i-th element comes from the i-th iterable argument.  The .__next__()
method continues until the shortest iterable in the argument sequence
is exhausted and then it raises StopIteration.""")


