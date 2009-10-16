"""
Interp-level definition of frequently used functionals.

"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, applevel
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.objectmodel import specialize
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
        x = space.int_w(space.int(w_x))
        if space.is_w(w_y, space.w_None):
            start, stop = 0, x
        else:
            start, stop = x, space.int_w(space.int(w_y))
        step = space.int_w(space.int(w_step))
        howmany = get_len_of_range(start, stop, step)
    except (ValueError, OverflowError, OperationError):
        # save duplication by redirecting every error to applevel
        return range_fallback(space, w_x, w_y, w_step)

    if space.config.objspace.std.withrangelist:
        return range_withspecialized_implementation(space, start,
                                                    step, howmany)
    res_w = [None] * howmany
    v = start
    for idx in range(howmany):
        res_w[idx] = space.wrap(v)
        v += step
    return space.newlist(res_w)
range_int = range
range_int.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]
del range # don't hide the builtin one

range_fallback = applevel(getsource(app_range), getfile(app_range)
                          ).interphook('range')

def range_withspecialized_implementation(space, start, step, howmany):
    assert space.config.objspace.std.withrangelist
    from pypy.objspace.std.rangeobject import W_RangeListObject
    return W_RangeListObject(start, step, howmany)


@specialize.arg(2)
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
    """Return the largest item in a sequence.

    If more than one argument is passed, return the maximum of them.
    """
    return min_max(space, __args__, "max")
max.unwrap_spec = [ObjSpace, Arguments]

def min(space, __args__):
    """Return the smallest item in a sequence.

    If more than one argument is passed, return the minimum of them.
    """
    return min_max(space, __args__, "min")
min.unwrap_spec = [ObjSpace, Arguments]

def map(space, w_func, collections_w):
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
    if not collections_w:
        msg = "map() requires at least two arguments"
        raise OperationError(space.w_TypeError, space.wrap(msg))
    num_collections = len(collections_w)
    none_func = space.is_w(w_func, space.w_None)
    if none_func and num_collections == 1:
        return space.call_function(space.w_list, collections_w[0])
    result_w = []
    iterators_w = [space.iter(w_seq) for w_seq in collections_w]
    num_iterators = len(iterators_w)
    while True:
        cont = False
        args_w = [space.w_None] * num_iterators
        for i in range(len(iterators_w)):
            try:
                args_w[i] = space.next(iterators_w[i])
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
            else:
                cont = True
        w_args = space.newtuple(args_w)
        if cont:
            if none_func:
                result_w.append(w_args)
            else:
                w_res = space.call(w_func, w_args)
                result_w.append(w_res)
        else:
            return space.newlist(result_w)
map.unwrap_spec = [ObjSpace, W_Root, "args_w"]

def sum(space, w_sequence, w_start=None):
    if space.is_w(w_start, space.w_None):
        w_start = space.wrap(0)
    elif space.is_true(space.isinstance(w_start, space.w_basestring)):
        msg = "sum() can't sum strings"
        raise OperationError(space.w_TypeError, space.wrap(msg))
    w_iter = space.iter(w_sequence)
    w_last = w_start
    while True:
        try:
            w_next = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        w_last = space.add(w_last, w_next)
    return w_last
sum.unwrap_spec = [ObjSpace, W_Root, W_Root]

def zip(space, sequences_w):
    """Return a list of tuples, where the nth tuple contains every nth item of
    each collection.

    If the collections have different lengths, zip returns a list as long as the
    shortest collection, ignoring the trailing items in the other collections.
    """
    if not sequences_w:
        return space.newlist([])
    result_w = []
    iterators_w = [space.iter(w_seq) for w_seq in sequences_w]
    while True:
        try:
            items_w = [space.next(w_it) for w_it in iterators_w]
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            return space.newlist(result_w)
        result_w.append(space.newtuple(items_w))
zip.unwrap_spec = [ObjSpace, "args_w"]

def reduce(space, w_func, w_sequence, w_initial=NoneNotWrapped):
    """ Apply function of two arguments cumulatively to the items of sequence,
        from left to right, so as to reduce the sequence to a single value.
        Optionally begin with an initial value.
    """
    w_iter = space.iter(w_sequence)
    if w_initial is None:
        try:
            w_initial = space.next(w_iter)
        except OperationError, e:
            if e.match(space, space.w_StopIteration):
                msg = "reduce() of empty sequence with no initial value"
                raise OperationError(space.w_TypeError, space.wrap(msg))
            raise
    w_result = w_initial
    while True:
        try:
            w_next = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        w_result = space.call_function(w_func, w_result, w_next)
    return w_result
reduce.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]

def filter(space, w_func, w_seq):
    """construct a list of those elements of collection for which function
       is True.  If function is None, then return the items in the sequence
       which are True.
    """
    if space.is_true(space.isinstance(w_seq, space.w_str)):
        return _filter_string(space, w_func, w_seq, space.w_str)
    if space.is_true(space.isinstance(w_seq, space.w_unicode)):
        return _filter_string(space, w_func, w_seq, space.w_unicode)
    if space.is_true(space.isinstance(w_seq, space.w_tuple)):
        return _filter_tuple(space, w_func, w_seq)
    w_iter = space.iter(w_seq)
    result_w = []
    none_func = space.is_w(w_func, space.w_None)
    while True:
        try:
            w_next = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        if none_func:
            w_keep = w_next
        else:
            w_keep = space.call_function(w_func, w_next)
        if space.is_true(w_keep):
            result_w.append(w_next)
    return space.newlist(result_w)

def _filter_tuple(space, w_func, w_tuple):
    none_func = space.is_w(w_func, space.w_None)
    length = space.int_w(space.len(w_tuple))
    result_w = []
    for i in range(length):
        w_item = space.getitem(w_tuple, space.wrap(i))
        if none_func:
            w_keep = w_item
        else:
            w_keep = space.call_function(w_func, w_item)
        if space.is_true(w_keep):
            result_w.append(w_item)
    return space.newtuple(result_w)

def _filter_string(space, w_func, w_string, w_str_type):
    none_func = space.is_w(w_func, space.w_None)
    if none_func and space.is_w(space.type(w_string), w_str_type):
        return w_string
    length = space.int_w(space.len(w_string))
    result_w = []
    for i in range(length):
        w_item = space.getitem(w_string, space.wrap(i))
        if none_func or space.is_true(space.call_function(w_func, w_item)):
            if not space.is_true(space.isinstance(w_item, w_str_type)):
                msg = "__getitem__ returned a non-string type"
                raise OperationError(space.w_TypeError, space.wrap(msg))
            result_w.append(w_item)
    w_empty = space.call_function(w_str_type)
    return space.call_method(w_empty, "join", space.newlist(result_w))

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


class W_Enumerate(Wrappable):

    def __init__(self, w_iter, w_start):
        self.w_iter = w_iter
        self.w_index = w_start

    def descr___new__(space, w_subtype, w_iterable):
        self = space.allocate_instance(W_Enumerate, w_subtype)
        self.__init__(space.iter(w_iterable), space.wrap(0))
        return space.wrap(self)

    def descr___iter__(self, space):
        return space.wrap(self)
    descr___iter__.unwrap_spec = ["self", ObjSpace]

    def descr_next(self, space):
        w_item = space.next(self.w_iter)
        w_index = self.w_index
        self.w_index = space.add(w_index, space.wrap(1))
        return space.newtuple([w_index, w_item])
    descr_next.unwrap_spec = ["self", ObjSpace]

    def descr___reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        w_new_inst = mod.get('enumerate_new')
        w_info = space.newtuple([self.w_iter, self.w_index])
        return space.newtuple([w_new_inst, w_info])
    descr___reduce__.unwrap_spec = ["self", ObjSpace]

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
    w_reversed_descr = space.lookup(w_sequence, "__reversed__")
    if w_reversed_descr is None:
        return space.wrap(W_ReversedIterator(space, w_sequence))
    return space.get_and_call_function(w_reversed_descr, w_sequence)
reversed.unwrap_spec = [ObjSpace, W_Root]

class W_ReversedIterator(Wrappable):

    def __init__(self, space, w_sequence):
        self.remaining = space.int_w(space.len(w_sequence)) - 1
        self.w_sequence = w_sequence

    def descr___iter__(self, space):
        return space.wrap(self)
    descr___iter__.unwrap_spec = ["self", ObjSpace]

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
    descr_next.unwrap_spec = ["self", ObjSpace]

    def descr___reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        w_new_inst = mod.get('reversed_new')
        info_w = [self.w_sequence, space.wrap(self.remaining)]
        w_info = space.newtuple(info_w)
        return space.newtuple([w_new_inst, w_info])
    descr___reduce__.unwrap_spec = ["self", ObjSpace]

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
        return space.int_w(space.int(w_obj))
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
# XXX __length_hint__()
##    __len__         = interp2app(W_XRangeIterator.descr_len),
    next            = interp2app(W_XRangeIterator.descr_next),
    __reduce__      = interp2app(W_XRangeIterator.descr_reduce),
)
