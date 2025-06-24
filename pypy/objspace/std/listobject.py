"""The builtin list implementation

Lists optimize their storage by holding certain primitive datatypes in
unwrapped form. For more information:

https://www.pypy.org/posts/2011/10/more-compact-lists-with-list-strategies-8229304944653956829.html

"""

import math
import operator
import sys

from rpython.rlib import debug, jit, rerased, rutf8
from rpython.rlib.listsort import make_timsort_class
from rpython.rlib.objectmodel import (
    import_from_mixin, instantiate, newlist_hint, resizelist_hint, specialize,
    resizable_list_extract_storage, wrap_into_resizable_list, we_are_translated)
from rpython.rlib.rarithmetic import ovfcheck, r_uint, intmask
from rpython.rlib import longlong2float, rgc
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib.rstring import StringBuilder

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    WrappedDefault, applevel, interp2app, unwrap_spec)
from pypy.interpreter.signature import Signature
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.bytesobject import W_BytesObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.iterobject import (
    W_FastListIterObject, W_ReverseSeqIterObject)
from pypy.objspace.std.sliceobject import (
    W_SliceObject, normalize_simple_slice, unwrap_start_stop)
from pypy.objspace.std.tupleobject import W_AbstractTupleObject
from pypy.objspace.std.unicodeobject import W_UnicodeObject
from pypy.objspace.std.util import get_positive_index, negate

__all__ = ['W_ListObject', 'make_range_list', 'make_empty_list_with_size']


UNROLL_CUTOFF = 5


def make_range_list(space, start, step, length):
    if length <= 0:
        strategy = space.fromcache(EmptyListStrategy)
        storage = strategy.erase(None)
    elif start == 0 and step == 1:
        strategy = space.fromcache(SimpleRangeListStrategy)
        storage = strategy.erase(None)
    else:
        strategy = space.fromcache(RangeListStrategy)
        storage = strategy.erase((start, step))
    return W_ListObject.from_storage_and_strategy(space, storage, strategy, length)


def make_empty_list(space):
    strategy = space.fromcache(EmptyListStrategy)
    storage = strategy.erase(None)
    return W_ListObject.from_storage_and_strategy(space, storage, strategy, 0)


def make_empty_list_with_size(space, hint):
    strategy = SizeListStrategy(space, hint)
    storage = strategy.erase(None)
    return W_ListObject.from_storage_and_strategy(space, storage, strategy, 0)


def get_strategy_from_list_object(space, list_w, sizehint):
    if not list_w:
        if sizehint != -1:
            return SizeListStrategy(space, sizehint)
        return space.fromcache(EmptyListStrategy)

    w_firstobj = list_w[0]

    if type(w_firstobj) is W_IntObject:
        if len(list_w) > 1:
            return _get_strategy_from_list_object_int(space, list_w)
        return space.fromcache(IntegerListStrategy)
    elif type(w_firstobj) is W_FloatObject:
        if len(list_w) > 1:
            return _get_strategy_from_list_object_float(space, list_w)
        return space.fromcache(FloatListStrategy)
    elif type(w_firstobj) is W_BytesObject:
        if len(list_w) > 1:
            return _get_strategy_from_list_object_bytes(space, list_w)
        return space.fromcache(BytesListStrategy)
    elif type(w_firstobj) is W_UnicodeObject and w_firstobj.is_ascii():
        if len(list_w) > 1:
            return _get_strategy_from_list_object_unicode(space, list_w)
        return space.fromcache(AsciiListStrategy)

    return space.fromcache(ObjectListStrategy)

@jit.look_inside_iff(lambda space, list_w:
        jit.loop_unrolling_heuristic(list_w, len(list_w), UNROLL_CUTOFF))
def _get_strategy_from_list_object_int(space, list_w):
    for i in range(1, len(list_w)):
        w_obj = list_w[i]
        if type(w_obj) is not W_IntObject:
            if type(w_obj) is W_FloatObject:
                return _get_strategy_from_list_object_int_or_float(space, list_w)
            return space.fromcache(ObjectListStrategy)
    return space.fromcache(IntegerListStrategy)

@jit.look_inside_iff(lambda space, list_w:
        jit.loop_unrolling_heuristic(list_w, len(list_w), UNROLL_CUTOFF))
def _get_strategy_from_list_object_float(space, list_w):
    for i in range(1, len(list_w)):
        w_obj = list_w[i]
        if type(w_obj) is not W_FloatObject:
            if type(w_obj) is W_IntObject:
                return _get_strategy_from_list_object_int_or_float(space, list_w)
            return space.fromcache(ObjectListStrategy)
    return space.fromcache(FloatListStrategy)

@jit.look_inside_iff(lambda space, list_w:
        jit.loop_unrolling_heuristic(list_w, len(list_w), UNROLL_CUTOFF))
def _get_strategy_from_list_object_bytes(space, list_w):
    for i in range(1, len(list_w)):
        if type(list_w[i]) is not W_BytesObject:
            return space.fromcache(ObjectListStrategy)
    return space.fromcache(BytesListStrategy)

@jit.look_inside_iff(lambda space, list_w:
        jit.loop_unrolling_heuristic(list_w, len(list_w), UNROLL_CUTOFF))
def _get_strategy_from_list_object_unicode(space, list_w):
    for i in range(1, len(list_w)):
        item = list_w[i]
        if type(item) is not W_UnicodeObject or not item.is_ascii():
            return space.fromcache(ObjectListStrategy)
    return space.fromcache(AsciiListStrategy)

@jit.look_inside_iff(lambda space, list_w:
        jit.loop_unrolling_heuristic(list_w, len(list_w), UNROLL_CUTOFF))
def _get_strategy_from_list_object_int_or_float(space, list_w):
    for w_obj in list_w:
        if type(w_obj) is W_IntObject:
            if longlong2float.can_encode_int32(w_obj.int_w(space)):
                continue    # ok
        elif type(w_obj) is W_FloatObject:
            if longlong2float.can_encode_float(w_obj.float_w(space)):
                continue    # ok
        return space.fromcache(ObjectListStrategy)
    return space.fromcache(IntOrFloatListStrategy)


def _get_printable_location(strategy_type, greenkey):
    return 'list__do_extend_from_iterable [%s, %s]' % (
        strategy_type,
        greenkey.iterator_greenkey_printable())


_do_extend_jitdriver = jit.JitDriver(
    name='list__do_extend_from_iterable',
    greens=['strategy_type', 'greenkey'],
    reds='auto',
    get_printable_location=_get_printable_location)

def _do_extend_from_iterable(space, w_list, w_iterable):
    w_iterator = space.iter(w_iterable)
    greenkey = space.iterator_greenkey(w_iterator)
    i = 0
    while True:
        _do_extend_jitdriver.jit_merge_point(
                greenkey=greenkey,
                strategy_type=type(w_list.strategy))
        try:
            w_list.append(space.next(w_iterator))
        except OperationError as e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        i += 1
    return i

def _get_printable_location(strategy_type, typ):
    return 'list.repr [%s, %s]' % (
        strategy_type,
        typ)

listrepr_jitdriver = jit.JitDriver(
    name='list.repr',
    greens=['strategy_type', 'typ'],
    reds='auto',
    get_printable_location=_get_printable_location)

def listrepr(space, w_currently_in_repr, w_list):
    length = w_list.length()
    if space.contains_w(w_currently_in_repr, w_list):
        return space.newtext('[...]')
    space.setitem(w_currently_in_repr, w_list, space.newint(1))
    try:
        assert length > 0
        builder = StringBuilder(3 * length + 2)
        builder.append('[')
        w_first = w_list.getitem(0)
        builder.append(space.text_w(space.repr(w_first)))
        typ = type(w_first)
        for i in range(1, length):
            listrepr_jitdriver.jit_merge_point(
                typ=typ,
                strategy_type=type(w_list.strategy))
            try:
                w_item = w_list.getitem(i)
            except IndexError:
                # repr changed the length, stop
                break
            builder.append(', ')
            builder.append(space.text_w(space.repr(w_item)))
        builder.append(']')
        return space.newtext(builder.build())
    finally:
        try:
            space.delitem(w_currently_in_repr, w_list)
        except OperationError as e:
            if not e.match(space, space.w_KeyError):
                raise


def list_unroll_condition(w_list1, space, w_list2):
    return (w_list1._unrolling_heuristic() or w_list2._unrolling_heuristic())

# YYY implement iterator_greenkey(!)

def _get_printable_location(strategy_type1, strategy_type2, typ):
    return 'list.eq [%s, %s, %s]' % (
        strategy_type1,
        strategy_type2,
        typ)


listeq_jitdriver = jit.JitDriver(
    name='list.eq',
    greens=['strategy_type1', 'strategy_type2', 'typ'],
    reds='auto',
    get_printable_location=_get_printable_location)

def _make_list_eq(withjitdriver):
    def list_eq(w_list, space, w_other):
        # needs to be safe against eq_w() mutating the w_lists behind our back
        length = w_list.length()
        if length != w_other.length():
            return space.w_False
        if not length:
            return space.w_True
        if withjitdriver:
            typ = type(w_list.getitem(0))

        i = 0
        while True:
            if withjitdriver:
                listeq_jitdriver.jit_merge_point(
                        strategy_type1=type(w_list.strategy),
                        strategy_type2=type(w_other.strategy),
                        typ=typ,
                        )
            try:
                w_item1 = w_list.getitem(i)
                w_item2 = w_other.getitem(i)
            except IndexError:
                break
            if not space.eq_w(w_item1, w_item2):
                return space.w_False

            i += 1

        # if the list length is different now, the list was modified by eq_w with
        l1 = w_list.length()
        l2 = w_other.length()
        if l1 != l2:
            return space.w_False
        return space.w_True
    return list_eq
_list_eq_withjitdriver = _make_list_eq(True)
_list_eq_unroll = jit.unroll_safe(_make_list_eq(False))


def list_eq(w_list, space, w_other):
    # we can't use look_inside_iff because the jitdriver will be found in two
    # different graphs then
    if jit.we_are_jitted() and list_unroll_condition(w_list, space, w_other):
        return _list_eq_unroll(w_list, space, w_other)
    else:
        return _list_eq_withjitdriver(w_list, space, w_other)


class W_ListObject(W_Root):
    strategy = None
    _length = 0

    def __init__(self, space, wrappeditems, sizehint=-1):
        # wrappeditems is resizable
        assert isinstance(wrappeditems, list)
        self.space = space
        if space.config.objspace.std.withliststrategies:
            self.strategy = get_strategy_from_list_object(space, wrappeditems,
                                                          sizehint)
        else:
            self.strategy = space.fromcache(ObjectListStrategy)
        self.init_from_list_w(wrappeditems)

    def _unrolling_heuristic(self):
        strategy = self.strategy
        return strategy._unrolling_heuristic(self)

    def _set_length(self, length):
        assert length >= 0
        self._length = length

    @staticmethod
    def from_storage_and_strategy(space, storage, strategy, length):
        self = instantiate(W_ListObject)
        self.space = space
        self._set_length(length)
        self.strategy = strategy
        self.lstorage = storage
        if not space.config.objspace.std.withliststrategies:
            self.switch_to_object_strategy()
        return self

    @staticmethod
    def newlist_bytes(space, list_b):
        strategy = space.fromcache(BytesListStrategy)
        storage = strategy.erase(resizable_list_extract_storage(list_b))
        return W_ListObject.from_storage_and_strategy(space, storage, strategy, len(list_b))

    @staticmethod
    def newlist_ascii(space, list_u):
        strategy = space.fromcache(AsciiListStrategy)
        storage = strategy.erase(resizable_list_extract_storage(list_u))
        return W_ListObject.from_storage_and_strategy(space, storage, strategy, len(list_u))

    @staticmethod
    def newlist_int(space, list_i):
        strategy = space.fromcache(IntegerListStrategy)
        storage = strategy.erase(resizable_list_extract_storage(list_i))
        return W_ListObject.from_storage_and_strategy(space, storage, strategy, len(list_i))

    @staticmethod
    def newlist_float(space, list_f):
        strategy = space.fromcache(FloatListStrategy)
        storage = strategy.erase(resizable_list_extract_storage(list_f))
        return W_ListObject.from_storage_and_strategy(space, storage, strategy, len(list_f))

    def __repr__(self):
        """ representation for debugging purposes """
        return "<%s %s %s %s>" % (self.__class__.__name__, self._length, self.strategy,
                               self.lstorage._x)

    def unwrap(w_list, space):
        # for tests only!
        items = [space.unwrap(w_item) for w_item in w_list.getitems()]
        return list(items)

    def switch_to_object_strategy(self):
        object_strategy = self.space.fromcache(ObjectListStrategy)
        if self.strategy is object_strategy:
            return
        list_w = self.getitems_fixedsize()
        self.strategy = object_strategy
        self.lstorage = object_strategy.erase(list_w)

    def _temporarily_as_objects(self):
        if self.strategy is self.space.fromcache(ObjectListStrategy):
            return self
        list_w = self.getitems_fixedsize()
        strategy = self.space.fromcache(ObjectListStrategy)
        storage = strategy.erase(list_w)
        w_objectlist = W_ListObject.from_storage_and_strategy(
                self.space, storage, strategy, len(list_w))
        return w_objectlist

    def convert_to_cpy_strategy(self, space):
        from pypy.module.cpyext.sequence import CPyListStorage, CPyListStrategy

        cpy_strategy = self.space.fromcache(CPyListStrategy)
        if self.strategy is cpy_strategy:
            return
        lst = self.getitems()
        self.strategy = cpy_strategy
        self.lstorage = cpy_strategy.erase(CPyListStorage(space, lst))

    # ___________________________________________________

    def init_from_list_w(self, list_w):
        """Initializes listobject by iterating through the given list of
        wrapped items, unwrapping them if neccessary and creating a
        new erased object as storage"""
        # list_w is resizable
        self._set_length(len(list_w))
        self.strategy.init_from_list_w(self, list_w)

    def clear(self, space):
        """Initializes (or overrides) the listobject as empty."""
        self.space = space
        if space.config.objspace.std.withliststrategies:
            strategy = space.fromcache(EmptyListStrategy)
        else:
            strategy = space.fromcache(ObjectListStrategy)
        self.strategy = strategy
        self._set_length(0)
        strategy.clear(self)

    def clone(self, sizehint=0):
        """Returns a clone by creating a new listobject
        with the same strategy and a copy of the storage.
        if a sizehint is given, the clone is overallocated to be that size."""
        return self.strategy.clone(self, sizehint)

    def _resize_hint(self, hint):
        """Ensure the underlying list has room for at least hint
        elements without changing the len() of the list"""
        return self.strategy._resize_hint(self, hint)

    def copy_into(self, other):
        """Used only when extending an EmptyList. Sets the EmptyLists
        strategy and storage according to the other W_List"""
        self.strategy.copy_into(self, other)

    def find_or_count(self, w_item, start=0, end=sys.maxint, count=False):
        """Find w_item in list[start:end]. If not found, raise ValueError.
        if count=True, count number of occurences instead"""
        return self.strategy.find_or_count(self, w_item, start, end, count)

    def append(self, w_item):
        """L.append(object) -- append object to end"""
        self.strategy.append(self, w_item)

    def length(self):
        res = self._length
        assert res >= 0
        return res

    def getitem(self, index):
        """Returns the wrapped object that is found in the
        list at the given index. The index must be unwrapped.
        May raise IndexError."""
        return self.strategy.getitem(self, index)

    def getslice(self, start, stop, step, length):
        """Returns a slice of the list defined by the arguments. Arguments must
        be normalized (i.e. using normalize_simple_slice or W_Slice.indices4).
        May raise IndexError."""
        return self.strategy.getslice(self, start, stop, step, length)

    def getitems(self):
        """Returns a list of all items after wrapping them. The result can
        share with the storage, if possible."""
        return self.strategy.getitems(self)

    def getitems_fixedsize(self):
        """Returns a fixed-size list of all items after wrapping them."""
        l = self.strategy.getitems_fixedsize(self)
        debug.make_sure_not_resized(l)
        return l

    def getitems_unroll(self):
        """Returns a fixed-size list of all items after wrapping them. The JIT
        will fully unroll this function."""
        l = self.strategy.getitems_unroll(self)
        debug.make_sure_not_resized(l)
        return l

    def getitems_copy(self):
        """Returns a copy of all items in the list. Same as getitems except for
        ObjectListStrategy."""
        return self.strategy.getitems_copy(self)

    def getitems_bytes(self):
        """Return the items in the list as unwrapped strings. If the list does
        not use the list strategy, return None."""
        return self.strategy.getitems_bytes(self)

    def getitems_ascii(self):
        """Return the items in the list as unwrapped unicodes. If the list does
        not use the list strategy, return None."""
        return self.strategy.getitems_ascii(self)

    def getitems_int(self):
        """Return the items in the list as unwrapped ints. If the list does not
        use the list strategy, return None."""
        return self.strategy.getitems_int(self)

    def getitems_float(self):
        """Return the items in the list as unwrapped floats. If the list does not
        use the list strategy, return None."""
        return self.strategy.getitems_float(self)
    # ___________________________________________________

    def mul(self, times):
        """Returns a copy of the list, multiplied by times.
        Argument must be unwrapped."""
        return self.strategy.mul(self, times)

    def inplace_mul(self, times):
        """Alters the list by multiplying its content by times."""
        self.strategy.inplace_mul(self, times)

    def deleteslice(self, start, step, length):
        """Deletes a slice from the list. Used in delitem and delslice.
        Arguments must be normalized (see getslice)."""
        self.strategy.deleteslice(self, start, step, length)

    def pop(self, index):
        """Pops an item from the list. Index must be normalized.
        May raise IndexError."""
        return self.strategy.pop(self, index)

    def pop_end(self):
        """ Pop the last element from the list."""
        return self.strategy.pop_end(self)

    def setitem(self, index, w_item):
        """Inserts a wrapped item at the given (unwrapped) index.
        May raise IndexError."""
        self.strategy.setitem(self, index, w_item)

    def setslice(self, start, step, slicelength, sequence_w):
        """Sets the slice of the list from start to start+step*slicelength to
        the sequence sequence_w.
        Used by setslice and setitem."""
        self.strategy.setslice(self, start, step, slicelength, sequence_w)

    def insert(self, index, w_item):
        """Inserts an item at the given position. Item must be wrapped,
        index not."""
        self.strategy.insert(self, index, w_item)

    def extend(self, w_iterable):
        '''L.extend(iterable) -- extend list by appending
        elements from the iterable'''
        self.strategy.extend(self, w_iterable)

    def reverse(self):
        """Reverses the list."""
        self.strategy.reverse(self)

    def sort(self, reverse):
        """Sorts the list ascending or descending depending on
        argument reverse. Argument must be unwrapped."""
        self.strategy.sort(self, reverse)

    def physical_size(self):
        """ return the physical (ie overallocated size) of the underlying list.
        """
        # exposed in __pypy__
        return self.strategy.physical_size(self)


    # exposed to app-level

    @staticmethod
    def descr_new(space, w_listtype, __args__):
        """T.__new__(S, ...) -> a new object with type S, a subtype of T"""
        w_obj = space.allocate_instance(W_ListObject, w_listtype)
        w_obj.clear(space)
        return w_obj

    def descr_init(self, space, __args__):
        """x.__init__(...) initializes x; see help(type(x)) for signature"""
        # this is on the silly side
        w_iterable, = __args__.parse_obj(
                None, 'list', init_signature, init_defaults)
        self.clear(space)
        if w_iterable is not None:
            self.extend(w_iterable)

    def descr_repr(self, space):
        return self.strategy.repr(self)

    def descr_eq(self, space, w_other):
        if not isinstance(w_other, W_ListObject):
            return space.w_NotImplemented
        return list_eq(self, space, w_other)

    descr_ne = negate(descr_eq)

    def _make_list_comparison(name):
        op = getattr(operator, name)

        def compare_unwrappeditems(self, space, w_list2):
            if not isinstance(w_list2, W_ListObject):
                return space.w_NotImplemented
            return _compare_unwrappeditems(self, space, w_list2)

        @jit.look_inside_iff(list_unroll_condition)
        def _compare_unwrappeditems(self, space, w_list2):
            # needs to be safe against eq_w() mutating the w_lists behind our
            # back
            # Search for the first index where items are different
            i = 0
            # XXX in theory, this can be implemented more efficiently as well.
            # let's not care for now
            while i < self.length() and i < w_list2.length():
                w_item1 = self.getitem(i)
                w_item2 = w_list2.getitem(i)
                if not space.eq_w(w_item1, w_item2):
                    return getattr(space, name)(w_item1, w_item2)
                i += 1
            # No more items to compare -- compare sizes
            return space.newbool(op(self.length(), w_list2.length()))

        return func_with_new_name(compare_unwrappeditems, 'descr_' + name)

    descr_lt = _make_list_comparison('lt')
    descr_le = _make_list_comparison('le')
    descr_gt = _make_list_comparison('gt')
    descr_ge = _make_list_comparison('ge')

    def descr_len(self, space):
        result = self.length()
        return space.newint(result)

    def descr_iter(self, space):
        return W_FastListIterObject(self)

    def descr_contains(self, space, w_obj):
        try:
            self.find_or_count(w_obj)
            return space.w_True
        except ValueError:
            return space.w_False

    def descr_add(self, space, w_list2):
        if not isinstance(w_list2, W_ListObject):
            return space.w_NotImplemented
        length1 = self.length()
        if not length1:
            # treat empty + list special, because the EmptyListStrategy.clone
            # ignores the sizehint for now
            return w_list2.clone()
        sizehint = 0
        if self.strategy is w_list2.strategy:
            length2 = w_list2.length()
            try:
                sizehint = ovfcheck(length1 + length2)
            except OverflowError:
                raise MemoryError
            assert sizehint >= 0
        w_clone = self.clone(sizehint=sizehint)
        w_clone.extend(w_list2)
        return w_clone

    def descr_inplace_add(self, space, w_iterable):
        if isinstance(w_iterable, W_ListObject):
            self.extend(w_iterable)
            return self

        try:
            self.extend(w_iterable)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return self

    def descr_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return self.mul(times)

    def descr_inplace_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        self.inplace_mul(times)
        return self

    def _unpack_slice(self, w_index):
        # important: unpack the slice before computing the length. the
        # __index__ methods can mutate the list and change its length.
        start, stop, step = w_index.unpack(self.space)
        length = self.length()
        return w_index.adjust_indices(start, stop, step, length)

    def descr_getitem(self, space, w_index):
        if isinstance(w_index, W_SliceObject):
            start, stop, step, slicelength = self._unpack_slice(w_index)
            assert slicelength >= 0
            if slicelength == 0:
                return make_empty_list(space)
            return self.getslice(start, stop, step, slicelength)

        try:
            index = space.getindex_w(w_index, space.w_IndexError, "list index")
            return self.getitem(index)
        except IndexError:
            raise oefmt(space.w_IndexError, "list index out of range")

    def descr_getslice(self, space, w_start, w_stop):
        length = self.length()
        start, stop = normalize_simple_slice(space, length, w_start, w_stop)

        slicelength = stop - start
        if slicelength == 0:
            return make_empty_list(space)
        return self.getslice(start, stop, 1, stop - start)

    def descr_setitem(self, space, w_index, w_any):
        if isinstance(w_index, W_SliceObject):
            # special case for l[:] = l2
            if (space.is_w(w_index.w_start, space.w_None) and
                    space.is_w(w_index.w_stop, space.w_None) and
                    space.is_w(w_index.w_step, space.w_None)):
                # use the extend logic
                if isinstance(w_any, W_ListObject):
                    if space.is_w(self, w_any):
                        return
                    w_other = w_any
                else:
                    sequence_w = space.listview(w_any)
                    w_other = W_ListObject(space, sequence_w)
                self.clear(space)
                w_other.copy_into(self)
                return

            start, stop, step, slicelength = self._unpack_slice(w_index)
            if isinstance(w_any, W_ListObject):
                w_other = w_any
            else:
                sequence_w = space.listview(w_any)
                w_other = W_ListObject(space, sequence_w)
            self.setslice(start, step, slicelength, w_other)
            return

        idx = space.getindex_w(w_index, space.w_IndexError, "list index")
        try:
            self.setitem(idx, w_any)
        except IndexError:
            raise oefmt(space.w_IndexError, "list index out of range")

    def descr_setslice(self, space, w_start, w_stop, w_iterable):
        length = self.length()
        start, stop = normalize_simple_slice(space, length, w_start, w_stop)

        if isinstance(w_iterable, W_ListObject):
            self.setslice(start, 1, stop - start, w_iterable)
        else:
            sequence_w = space.listview(w_iterable)
            w_other = W_ListObject(space, sequence_w)
            self.setslice(start, 1, stop - start, w_other)

    def descr_delitem(self, space, w_idx):
        if isinstance(w_idx, W_SliceObject):
            start, stop, step, slicelength = self._unpack_slice(w_idx)
            self.deleteslice(start, step, slicelength)
            return

        idx = space.getindex_w(w_idx, space.w_IndexError, "list index")
        try:
            self.pop(idx)
        except IndexError:
            raise oefmt(space.w_IndexError, "list index out of range")

    def descr_delslice(self, space, w_start, w_stop):
        length = self.length()
        start, stop = normalize_simple_slice(space, length, w_start, w_stop)
        self.deleteslice(start, 1, stop - start)

    def descr_reversed(self, space):
        'L.__reversed__() -- return a reverse iterator over the list'
        return W_ReverseSeqIterObject(space, self, -1)

    def descr_reverse(self, space):
        'L.reverse() -- reverse *IN PLACE*'
        self.reverse()

    def descr_count(self, space, w_value):
        '''L.count(value) -> integer -- return number of
        occurrences of value'''
        i = self.find_or_count(w_value, count=True)
        return space.newint(i)

    @unwrap_spec(index=int)
    def descr_insert(self, space, index, w_value):
        'L.insert(index, object) -- insert object before index'
        length = self.length()
        index = get_positive_index(index, length)
        self.insert(index, w_value)

    @unwrap_spec(index=int)
    def descr_pop(self, space, index=-1):
        '''L.pop([index]) -> item -- remove and return item at
        index (default last)'''
        length = self.length()
        if length <= 0: # length cannot actually be < 0, but this way the jit learns that too
            raise oefmt(space.w_IndexError, "pop from empty list")
        # clearly differentiate between list.pop() and list.pop(index)
        if index == -1:
            return self.pop_end()  # cannot raise because list is not empty
        try:
            return self.pop(index)
        except IndexError:
            raise oefmt(space.w_IndexError, "pop index out of range")

    def descr_remove(self, space, w_value):
        'L.remove(value) -- remove first occurrence of value'
        # needs to be safe against eq_w() mutating the w_list behind our back
        try:
            i = self.find_or_count(w_value, 0, sys.maxint)
        except ValueError:
            raise oefmt(space.w_ValueError,
                        "list.remove(): %R is not in list", w_value)
        if i < self.length():  # otherwise list was mutated
            self.pop(i)

    @unwrap_spec(w_start=WrappedDefault(0), w_stop=WrappedDefault(sys.maxint))
    def descr_index(self, space, w_value, w_start, w_stop):
        '''L.index(value, [start, [stop]]) -> integer -- return
        first index of value'''
        # needs to be safe against eq_w() mutating the w_list behind our back
        size = self.length()
        i, stop = unwrap_start_stop(space, size, w_start, w_stop)
        # note that 'i' and 'stop' can be bigger than the length of the list
        try:
            i = self.find_or_count(w_value, i, stop)
        except ValueError:
            raise oefmt(space.w_ValueError, "%R is not in list", w_value)
        return space.newint(i)

    @unwrap_spec(reverse=bool)
    def descr_sort(self, space, w_cmp=None, w_key=None, reverse=False):
        """ L.sort(cmp=None, key=None, reverse=False) -- stable
        sort *IN PLACE*;
        cmp(x, y) -> -1, 0, 1"""
        has_cmp = not space.is_none(w_cmp)
        has_key = not space.is_none(w_key)

        # create and setup a TimSort instance
        if has_cmp:
            if has_key:
                sorterclass = CustomKeyCompareSort
            else:
                sorterclass = CustomCompareSort
        else:
            if has_key:
                sorterclass = CustomKeySort
            else:
                if self.strategy is space.fromcache(ObjectListStrategy):
                    sorterclass = SimpleSort
                else:
                    self.sort(reverse)
                    return

        sorter = sorterclass(self.getitems(), self.length())
        sorter.space = space
        sorter.w_cmp = w_cmp

        try:
            strategy = self.strategy
            # The list is temporarily made empty, so that mutations performed
            # by comparison functions can't affect the slice of memory we're
            # sorting (allowing mutations during sorting is an IndexError or
            # core-dump factory, since the storage may change).
            self.__init__(space, [])

            # wrap each item in a KeyContainer if needed
            if has_key:
                # XXX inefficient for unwrapped strategies:
                # we wrap the elements twice, once for the key, and once to get
                # KeyContainers. Then unwrap carefully in the __init__ call below.
                # Could type-specialize this.
                _compute_keys_for_sorting(strategy, sorter.list, w_key)

            # Reverse sort stability achieved by initially reversing the list,
            # applying a stable forward sort, then reversing the final result.
            if reverse:
                sorter.list.reverse()

            # perform the sort
            sorter.sort()

            # reverse again
            if reverse:
                sorter.list.reverse()

        finally:
            # unwrap each item if needed
            if has_key:
                _unwrap_sorting_keys(sorter)

            # check if the user mucked with the list during the sort
            mucked = self.length() > 0

            # put the items back into the list
            self.__init__(space, sorter.list)

        if mucked:
            raise oefmt(space.w_ValueError, "list modified during sort")

def get_printable_location_sortkey(strategy_type, tp):
    return "_compute_keys_for_sorting [%s, %s]" % (strategy_type, tp.getname(tp.space), )

sortkey_jmp = jit.JitDriver(
    greens=['strategy_type', 'tp'],
    reds='auto',
    name='_compute_keys_for_sorting',
    get_printable_location=get_printable_location_sortkey)

def _compute_keys_for_sorting(strategy, list_w, w_callable):
    space = strategy.space
    i = 0
    # XXX would like a new API space.greenkey_for_callable here
    # (also in min/max and map/filter)
    tp = space.type(w_callable)
    while i < len(list_w):
        # bit weird: we have a list_w at this point, but we still specialize on
        # the strategy to distinguish the cases better
        sortkey_jmp.jit_merge_point(tp=tp, strategy_type=type(strategy))
        w_item = list_w[i]
        w_keyitem = space.call_function(w_callable, w_item)
        list_w[i] = KeyContainer(w_keyitem, w_item)
        i += 1


def _unwrap_sorting_keys(sorter):
    for i in range(sorter.listlength):
        w_obj = sorter.list[i]
        if isinstance(w_obj, KeyContainer):
            sorter.list[i] = w_obj.w_item

def get_printable_location_find(count, strategy_type, tp):
    if count:
        start = "list.count"
    else:
        start = "list.find"
    return "%s [%s, %s]" % (start, strategy_type, tp.getname(tp.space), )

find_or_count_jmp = jit.JitDriver(
    greens=['count', 'strategy_type', 'tp'],
    reds='auto',
    name='list.find_or_count',
    get_printable_location=get_printable_location_find)

class ListStrategy(object):

    def __init__(self, space):
        self.space = space

    def get_sizehint(self, sizehint=-1):
        return sizehint

    def init_from_list_w(self, w_list, list_w):
        raise NotImplementedError

    def clone(self, w_list, sizehint=0):
        raise NotImplementedError

    def copy_into(self, w_list, w_other):
        raise NotImplementedError

    def _resize_hint(self, w_list, hint):
        raise NotImplementedError

    def find_or_count(self, w_list, w_item, start, stop, count):
        space = self.space
        i = start
        result = 0
        # needs to be safe against eq_w mutating stuff
        tp = space.type(w_item)
        while i < stop and i < w_list.length():
            find_or_count_jmp.jit_merge_point(tp=tp, strategy_type=type(self), count=count)
            if space.eq_w(w_item, w_list.getitem(i)):
                if count:
                    result += 1
                else:
                    return i
            i += 1
        if count:
            return result
        # not find case, not found
        raise ValueError

    def getitem(self, w_list, index):
        raise NotImplementedError

    def getslice(self, w_list, start, stop, step, length):
        raise NotImplementedError

    def getitems(self, w_list):
        return self.getitems_copy(w_list)

    def getitems_copy(self, w_list):
        raise NotImplementedError

    def getitems_bytes(self, w_list):
        return None

    def getitems_ascii(self, w_list):
        return None

    def getitems_int(self, w_list):
        return None

    def getitems_float(self, w_list):
        return None

    def getstorage_copy(self, w_list):
        raise NotImplementedError

    def append(self, w_list, w_item):
        raise NotImplementedError

    def mul(self, w_list, times):
        w_newlist = w_list.clone()
        w_newlist.inplace_mul(times)
        return w_newlist

    def inplace_mul(self, w_list, times):
        raise NotImplementedError

    def deleteslice(self, w_list, start, step, slicelength):
        raise NotImplementedError

    def pop(self, w_list, index):
        raise NotImplementedError

    def pop_end(self, w_list):
        return self.pop(w_list, w_list.length() - 1)

    def setitem(self, w_list, index, w_item):
        raise NotImplementedError

    def setslice(self, w_list, start, step, slicelength, sequence_w):
        raise NotImplementedError

    def insert(self, w_list, index, w_item):
        raise NotImplementedError

    def extend(self, w_list, w_any):
        from pypy.objspace.std.tupleobject import W_AbstractTupleObject
        space = self.space
        if type(w_any) is W_ListObject or (isinstance(w_any, W_ListObject) and
                                           space._uses_list_iter(w_any)):
            self._extend_from_list(w_list, w_any)
        elif (isinstance(w_any, W_AbstractTupleObject) and
                not w_any.user_overridden_class and
                w_any.length() < UNROLL_CUTOFF and
                w_list.length() > 0
        ):
            self._extend_from_tuple(w_list, w_any.tolist())
        elif space.is_generator(w_any):
            w_any.unpack_into_w(w_list)
        else:
            self._extend_from_iterable(w_list, w_any)

    def _extend_from_list(self, w_list, w_other):
        raise NotImplementedError

    @jit.look_inside_iff(lambda self, w_list, tup_w:
            jit.loop_unrolling_heuristic(tup_w, len(tup_w), UNROLL_CUTOFF))
    def _extend_from_tuple(self, w_list, tup_w):
        try:
            newsize_hint = ovfcheck(w_list.length() + len(tup_w))
        except OverflowError:
            pass
        else:
            w_list._resize_hint(newsize_hint)
        for w_element in tup_w:
            w_list.append(w_element)

    def _extend_from_iterable(self, w_list, w_iterable):
        """Extend w_list from a generic iterable"""
        length_hint = self.space.length_hint(w_iterable, 0)
        if length_hint:
            try:
                newsize_hint = ovfcheck(w_list.length() + length_hint)
            except OverflowError:
                pass
            else:
                w_list._resize_hint(newsize_hint)

        extended = _do_extend_from_iterable(self.space, w_list, w_iterable)

        # cut back if the length hint was too large
        if extended < length_hint:
            w_list._resize_hint(w_list.length())

    def reverse(self, w_list):
        raise NotImplementedError

    def sort(self, w_list, reverse):
        raise NotImplementedError

    def is_empty_strategy(self):
        return False

    def physical_size(self, w_list):
        raise oefmt(self.space.w_ValueError, "can't get physical size of list")

    def repr(self, w_list):
        space = self.space
        if w_list.length() == 0:
            return space.newtext('[]')
        return listrepr(space, space.get_objects_in_repr(), w_list)

    def _unrolling_heuristic(self, w_list):
        # default implementation: we will only go by size, not whether the list
        # is virtual
        size = w_list.length()
        return size == 0 or (jit.isconstant(size) and size <= UNROLL_CUTOFF)


class EmptyListStrategy(ListStrategy):
    """EmptyListStrategy is used when a W_List withouth elements is created.
    The storage is None. When items are added to the W_List a new RPython list
    is created and the strategy and storage of the W_List are changed depending
    to the added item.
    W_Lists do not switch back to EmptyListStrategy when becoming empty again.
    """

    def __init__(self, space):
        ListStrategy.__init__(self, space)

    def init_from_list_w(self, w_list, list_w):
        assert len(list_w) == 0
        w_list.lstorage = self.erase(None)

    def clear(self, w_list):
        w_list.lstorage = self.erase(None)

    erase, unerase = rerased.new_erasing_pair("empty")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def clone(self, w_list, sizehint=0):
        return W_ListObject.from_storage_and_strategy(
                self.space, w_list.lstorage, self, 0)

    def copy_into(self, w_list, w_other):
        pass

    def _resize_hint(self, w_list, hint):
        assert hint >= 0
        if hint:
            w_list.strategy = SizeListStrategy(self.space, hint)

    def find_or_count(self, w_list, w_item, start, stop, count):
        if count:
            return 0
        raise ValueError

    def getitem(self, w_list, index):
        raise IndexError

    def getslice(self, w_list, start, stop, step, length):
        # will never be called because the empty list case is already caught in
        # getslice__List_ANY_ANY and getitem__List_Slice
        return W_ListObject(self.space, [])

    def getitems(self, w_list):
        return []

    def getitems_copy(self, w_list):
        return []
    getitems_fixedsize = func_with_new_name(getitems_copy,
                                            "getitems_fixedsize")
    getitems_unroll = getitems_fixedsize

    def getstorage_copy(self, w_list):
        return self.erase(None)

    def switch_to_correct_strategy(self, w_list, w_item, sizehint=-1):
        if type(w_item) is W_IntObject:
            strategy = self.space.fromcache(IntegerListStrategy)
        elif type(w_item) is W_BytesObject:
            strategy = self.space.fromcache(BytesListStrategy)
        elif type(w_item) is W_UnicodeObject and w_item.is_ascii():
            strategy = self.space.fromcache(AsciiListStrategy)
        elif type(w_item) is W_FloatObject:
            strategy = self.space.fromcache(FloatListStrategy)
        else:
            strategy = self.space.fromcache(ObjectListStrategy)

        storage = strategy.get_empty_storage(self.get_sizehint(sizehint))
        w_list.strategy = strategy
        w_list.lstorage = storage

    def append(self, w_list, w_item):
        # 4, to follow the usual overallocation growth pattern
        self.switch_to_correct_strategy(w_list, w_item, sizehint=4)
        w_list.append(w_item)

    def inplace_mul(self, w_list, times):
        return

    def deleteslice(self, w_list, start, step, slicelength):
        pass

    def pop(self, w_list, index):
        # will not be called because IndexError was already raised in
        # list_pop__List_ANY
        raise IndexError

    def setitem(self, w_list, index, w_item):
        raise IndexError

    def setslice(self, w_list, start, step, slicelength, w_other):
        strategy = w_other.strategy
        if step != 1:
            len2 = w_other.length()
            if len2 == 0:
                return
            else:
                raise oefmt(self.space.w_ValueError,
                            "attempt to assign sequence of size %d to extended "
                            "slice of size %d", len2, 0)
        storage = strategy.getstorage_copy(w_other)
        w_list.strategy = strategy
        w_list.lstorage = storage
        w_list._set_length(w_other.length())

    def sort(self, w_list, reverse):
        return

    def insert(self, w_list, index, w_item):
        assert index == 0
        self.append(w_list, w_item)

    def _extend_from_list(self, w_list, w_other):
        w_other.copy_into(w_list)

    def _extend_from_iterable(self, w_list, w_iterable):
        space = self.space
        if (isinstance(w_iterable, W_AbstractTupleObject)
                and space._uses_tuple_iter(w_iterable)):
            w_list.__init__(space, w_iterable.getitems_copy())
            return

        # need to copy because the *list can share with w_iterable
        intlist = space.unpackiterable_int(w_iterable)
        if intlist is not None:
            w_list.strategy = strategy = space.fromcache(IntegerListStrategy)
            w_list.lstorage = strategy.erase(intlist[:])
            w_list._set_length(len(intlist))
            return

        floatlist = space.unpackiterable_float(w_iterable)
        if floatlist is not None:
            w_list.strategy = strategy = space.fromcache(FloatListStrategy)
            w_list.lstorage = strategy.erase(floatlist[:])
            w_list._set_length(len(floatlist))
            return

        byteslist = space.listview_bytes(w_iterable)
        if byteslist is not None:
            w_list.strategy = strategy = space.fromcache(BytesListStrategy)
            w_list.lstorage = strategy.erase(byteslist[:])
            w_list._set_length(len(byteslist))
            return

        unilist = space.listview_ascii(w_iterable)
        if unilist is not None:
            w_list.strategy = strategy = space.fromcache(AsciiListStrategy)
            w_list.lstorage = strategy.erase(unilist[:])
            w_list._set_length(len(unilist))
            return

        ListStrategy._extend_from_iterable(self, w_list, w_iterable)

    def reverse(self, w_list):
        pass

    def is_empty_strategy(self):
        return True

    def physical_size(self, w_list):
        return 0

    def repr(self, w_list):
        space = self.space
        return space.newtext('[]')

    def _unrolling_heuristic(self, w_list):
        return True


class SizeListStrategy(EmptyListStrategy):
    """Like empty, but when modified it'll preallocate the size to sizehint."""
    def __init__(self, space, sizehint):
        self.sizehint = sizehint
        ListStrategy.__init__(self, space)

    def get_sizehint(self, sizehint=-1):
        return self.sizehint

    def _resize_hint(self, w_list, hint):
        assert hint >= 0
        self.sizehint = hint


class BaseRangeListStrategy(ListStrategy):
    def switch_to_integer_strategy(self, w_list):
        items = self._getitems_range(w_list, False)
        strategy = w_list.strategy = self.space.fromcache(IntegerListStrategy)
        w_list.lstorage = strategy.erase(resizable_list_extract_storage(items))

    def wrap(self, intval):
        return self.space.newint(intval)

    def unwrap(self, w_int):
        assert type(w_int) is W_IntObject
        return w_int.intval

    def init_from_list_w(self, w_list, list_w):
        raise NotImplementedError

    def clone(self, w_list, sizehint=0):
        storage = w_list.lstorage  # lstorage is tuple, no need to clone
        w_clone = W_ListObject.from_storage_and_strategy(self.space, storage,
                                                         self, w_list.length())
        return w_clone

    def _resize_hint(self, w_list, hint):
        # XXX: this could be supported
        assert hint >= 0

    def copy_into(self, w_list, w_other):
        w_other.strategy = self
        w_other.lstorage = w_list.lstorage
        w_other._set_length(w_list._length)

    def getitem(self, w_list, i):
        return self.wrap(self._getitem_unwrapped(w_list, i))

    def getitems_int(self, w_list):
        return self._getitems_range(w_list, False)

    def getitems_copy(self, w_list):
        return self._getitems_range(w_list, True)

    def getstorage_copy(self, w_list):
        # tuple is immutable
        return w_list.lstorage

    @jit.dont_look_inside
    def getitems_fixedsize(self, w_list):
        return self._getitems_range_unroll(w_list, True)

    def getitems_unroll(self, w_list):
        return self._getitems_range_unroll(w_list, True)

    def getslice(self, w_list, start, stop, step, length):
        self.switch_to_integer_strategy(w_list)
        return w_list.getslice(start, stop, step, length)

    def append(self, w_list, w_item):
        if type(w_item) is W_IntObject:
            self.switch_to_integer_strategy(w_list)
        else:
            w_list.switch_to_object_strategy()
        w_list.append(w_item)

    def inplace_mul(self, w_list, times):
        self.switch_to_integer_strategy(w_list)
        w_list.inplace_mul(times)

    def deleteslice(self, w_list, start, step, slicelength):
        self.switch_to_integer_strategy(w_list)
        w_list.deleteslice(start, step, slicelength)

    def setitem(self, w_list, index, w_item):
        self.switch_to_integer_strategy(w_list)
        w_list.setitem(index, w_item)

    def setslice(self, w_list, start, step, slicelength, sequence_w):
        self.switch_to_integer_strategy(w_list)
        w_list.setslice(start, step, slicelength, sequence_w)

    def insert(self, w_list, index, w_item):
        self.switch_to_integer_strategy(w_list)
        w_list.insert(index, w_item)

    def extend(self, w_list, w_any):
        self.switch_to_integer_strategy(w_list)
        w_list.extend(w_any)

    def reverse(self, w_list):
        self.switch_to_integer_strategy(w_list)
        w_list.reverse()

    def sort(self, w_list, reverse):
        step = self.step(w_list)
        if step > 0 and reverse or step < 0 and not reverse:
            self.switch_to_integer_strategy(w_list)
            w_list.sort(reverse)

    # default _unrolling_heuristic is fine


class SimpleRangeListStrategy(BaseRangeListStrategy):
    """SimpleRangeListStrategy is used when a list is created using the range
       method providing only positive length. The storage is a one element tuple
       with positive integer storing length."""

    erase, unerase = rerased.new_erasing_pair("simple_range")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def find_or_count(self, w_list, w_obj, startindex, stopindex, count):
        if type(w_obj) is W_IntObject:
            obj = self.unwrap(w_obj)
            length = w_list.length()
            if 0 <= obj < length and startindex <= obj < stopindex:
                if count:
                    return 1
                return obj
            else:
                if count:
                    return 0
                raise ValueError
        return ListStrategy.find_or_count(
            self, w_list, w_obj, startindex, stopindex, count)

    def step(self, w_list):
        return 1

    def _getitem_unwrapped(self, w_list, i):
        length = w_list.length()
        if i < 0:
            i += length
            if i < 0:
                raise IndexError
        elif i >= length:
            raise IndexError
        return i

    @specialize.arg(2)
    def _getitems_range(self, w_list, wrap_items):
        length = w_list.length()
        if wrap_items:
            r = [None] * length
        else:
            r = [0] * length
        i = 0
        while i < length:
            if wrap_items:
                r[i] = self.wrap(i)
            else:
                r[i] = i
            i += 1

        return r

    _getitems_range_unroll = jit.unroll_safe(
            func_with_new_name(_getitems_range, "_getitems_range_unroll"))

    def pop_end(self, w_list):
        new_length = w_list.length() - 1
        w_list._set_length(new_length)
        w_result = self.wrap(new_length)
        if new_length == 0:
            strategy = w_list.strategy = self.space.fromcache(EmptyListStrategy)
            w_list.lstorage = strategy.erase(None)
        return w_result

    def pop(self, w_list, index):
        self.switch_to_integer_strategy(w_list)
        return w_list.pop(index)


class RangeListStrategy(BaseRangeListStrategy):
    """RangeListStrategy is used when a list is created using the range method.
    The storage is a tuple containing only three integers start, step and
    length and elements are calculated based on these values.  On any operation
    destroying the range (inserting, appending non-ints) the strategy is
    switched to IntegerListStrategy."""

    erase, unerase = rerased.new_erasing_pair("range")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def find_or_count(self, w_list, w_obj, startindex, stopindex, count):
        if type(w_obj) is W_IntObject:
            obj = self.unwrap(w_obj)
            start, step = self.unerase(w_list.lstorage)
            length = w_list.length()
            if ((step > 0 and start <= obj <= start + (length - 1) * step and
                 (start - obj) % step == 0) or
                (step < 0 and start + (length - 1) * step <= obj <= start and
                 (start - obj) % step == 0)):
                index = (obj - start) // step
            else:
                if count:
                    return 0
                raise ValueError
            if startindex <= index < stopindex:
                if count:
                    return 1
                return index
            if count:
                return 0
            raise ValueError
        return ListStrategy.find_or_count(
            self, w_list, w_obj, startindex, stopindex, count)

    def step(self, w_list):
        return self.unerase(w_list.lstorage)[1]

    def _getitem_unwrapped(self, w_list, i):
        start, step = self.unerase(w_list.lstorage)
        length = w_list.length()
        if i < 0:
            i += length
            if i < 0:
                raise IndexError
        elif i >= length:
            raise IndexError
        return start + i * step

    @specialize.arg(2)
    def _getitems_range(self, w_list, wrap_items):
        start, step = self.unerase(w_list.lstorage)
        length = w_list.length()
        if wrap_items:
            r = [None] * length
        else:
            r = [0] * length
        i = start
        n = 0
        while n < length:
            if wrap_items:
                r[n] = self.wrap(i)
            else:
                r[n] = i
            i += step
            n += 1

        return r

    _getitems_range_unroll = jit.unroll_safe(
            func_with_new_name(_getitems_range, "_getitems_range_unroll"))

    def pop_end(self, w_list):
        start, step = self.unerase(w_list.lstorage)
        length = w_list.length()
        w_result = self.wrap(start + (length - 1) * step)
        new = self.erase((start, step))
        w_list._length -= 1
        w_list.lstorage = new
        return w_result

    def pop(self, w_list, index):
        start, step = self.unerase(w_list.lstorage)
        length = w_list.length()
        if index == 0:
            w_result = self.wrap(start)
            new = self.erase((start + step, step))
            w_list._length -= 1
            w_list.lstorage = new
            return w_result
        elif index == length - 1:
            return self.pop_end(w_list)
        else:
            self.switch_to_integer_strategy(w_list)
            return w_list.pop(index)


class AbstractUnwrappedStrategy(object):

    _need_clearing = True

    def wrap(self, unwrapped):
        raise NotImplementedError

    def unwrap(self, wrapped):
        raise NotImplementedError

    def _quick_cmp(self, a, b):
        """ do a quick comparison between two unwrapped elements. """
        raise NotImplementedError("abstract base class")

    @staticmethod
    def unerase(storage):
        raise NotImplementedError("abstract base class")

    @staticmethod
    def erase(obj):
        raise NotImplementedError("abstract base class")

    def is_correct_type(self, w_obj):
        raise NotImplementedError("abstract base class")

    def list_is_correct_type(self, w_list):
        raise NotImplementedError("abstract base class")

    # ___________________________________________________
    # resizable list support

    def _arrayclear(self, items, start, stop):
        if not self._need_clearing:
            return
        for i in range(start, stop):
            items[i] = self._none_value

    @staticmethod
    @jit.oopspec('list.ll_arraymove(array, source_start, dest_start, length)')
    def _arraymove(array, source_start, dest_start, length):
        rgc.hl_arraymove(array, source_start, dest_start, length)

    @staticmethod
    @jit.oopspec('list.ll_arraycopy(source, dest, source_start, dest_start, length)')
    def _arraycopy(source, dest, source_start, dest_start, length):
        return rgc.hl_arraycopy(source, dest, source_start, dest_start, length)

    def _resize_ge(self, w_list, newsize):
        """This is called with 'newsize' larger than the current length of the
        list.  If the list storage doesn't have enough space, then really
        allocate more space.  In the common case where we already overallocated
        enough, then this is a very fast operation.
        """
        l = self.unerase(w_list.lstorage)
        cond = len(l) < newsize
        if jit.isconstant(len(l)) and jit.isconstant(newsize):
            if cond:
                self._list_resize_hint_really(self, w_list, newsize, True)
        else:
            func = self._list_resize_hint_really
            jit.conditional_call(cond,
                                 func, self, w_list, newsize, True)
        w_list._set_length(newsize)

    def _resize_le(self, w_list, newsize):
        """This is called with 'newsize' smaller than the current physical
        length of the list.  If 'newsize' falls lower than half the allocated
        size, proceed with the shrinking the list.
        """
        l = self.unerase(w_list.lstorage)
        cond = newsize < (len(l) >> 1) - 5
        # note: overallocate=False should be safe here
        if jit.isconstant(len(l)) and jit.isconstant(newsize):
            if cond:
                self._list_resize_hint_really(self, w_list, newsize, False)
        else:
            func = self._list_resize_hint_really
            jit.conditional_call(cond, func, self, w_list, newsize,
                                 False)
        w_list._set_length(newsize)

    def _resize_hint(self, w_list, hint):
        """Ensure l.items has room for at least newsize elements without
        setting l.length to newsize.

        Used before (and after) a batch operation that will likely grow the
        list to the newsize (and after the operation incase the initial
        guess lied).
        """
        assert hint >= 0, "negative list length"
        l = self.unerase(w_list.lstorage)
        allocated = len(l)
        if hint > allocated:
            overallocate = True
        elif hint < (allocated >> 1) - 5:
            overallocate = False
        else:
            return
        self._list_resize_hint_really(self, w_list, hint, overallocate)


    @staticmethod # bizarre jit hack to support conditional_call
    @jit.look_inside_iff(
        lambda self, w_list, newsize, overallocate:
            jit.isconstant(len(self.unerase(w_list.lstorage))) and
                jit.isconstant(newsize))
    def _list_resize_hint_really(self, w_list, newsize, overallocate):
        """
        Ensure w_list has room for at least newsize elements.  Note that
        w_list.lstorage may change, and even if newsize is less than
        w_list.length() on entry.
        """
        # see comments in _ll_list_resize_really
        if newsize <= 0:
            w_list._set_length(0)
            w_list.lstorage = self.erase([])
            return
        elif overallocate:
            if newsize < 9:
                some = 3
            else:
                some = 6
            some += newsize >> 3
            new_allocated = newsize + some
        else:
            new_allocated = newsize
        l = self.unerase(w_list.lstorage)
        assert new_allocated >= 0
        newitems = [self._none_value] * new_allocated
        before_len = w_list.length()
        if before_len:
            if before_len < newsize:
                p = before_len
            else:
                p = newsize
            items = self.unerase(w_list.lstorage)
            self._arraycopy(items, newitems, 0, 0, p)
        w_list.lstorage = self.erase(newitems)

    # ___________________________________________________

    def init_from_list_w(self, w_list, list_w):
        l = self._init_from_list_w_helper(list_w)
        w_list.lstorage = self.erase(l)

    @jit.look_inside_iff(lambda space, list_w:
            jit.loop_unrolling_heuristic(list_w, len(list_w), UNROLL_CUTOFF))
    def _init_from_list_w_helper(self, list_w):
        return [self.unwrap(w_item) for w_item in list_w]

    def get_empty_storage(self, sizehint):
        if sizehint < 0:
            return self.erase([])
        newitems = [self._none_value] * sizehint
        return self.erase(newitems)

    def clone(self, w_list, sizehint=0):
        l = self.unerase(w_list.lstorage)
        if sizehint:
            assert sizehint >= w_list.length()
            l2 = [self._none_value] * sizehint
            self._arraycopy(l, l2, 0, 0, w_list.length())
        else:
            l2 = l[:]
        storage = self.erase(l2)
        w_clone = W_ListObject.from_storage_and_strategy(
                self.space, storage, self, w_list.length())
        return w_clone

    def copy_into(self, w_list, w_other):
        w_other.strategy = self
        length = w_list.length()
        items = self.unerase(w_list.lstorage)[:length]
        w_other.lstorage = self.erase(items)
        w_other._set_length(length)

    def find_or_count(self, w_list, w_obj, start, stop, count):
        if self.is_correct_type(w_obj):
            return self._safe_find_or_count(
                self.unerase(w_list.lstorage), w_list.length(),
                self.unwrap(w_obj), start, stop, count)
        return ListStrategy.find_or_count(
            self, w_list, w_obj, start, stop, count)

    def _safe_find_or_count(self, l, length, obj, start, stop, count):
        result = 0
        for i in range(start, min(stop, length)):
            val = l[i]
            if val == obj:
                if count:
                    result += 1
                else:
                    return i
        if count:
            return result
        raise ValueError

    def getitem(self, w_list, index):
        l = self.unerase(w_list.lstorage)
        length = w_list.length()
        if r_uint(index) >= r_uint(length):
            index = r_uint(index) + r_uint(length)
            if index >= r_uint(length):
                raise IndexError
            index = intmask(index)
        r = l[index]
        return self.wrap(r)

    def getitems_copy(self, w_list):
        storage = self.unerase(w_list.lstorage)
        length = w_list.length()
        if length == 0:
            return []
        res = [None] * length
        prevvalue = storage[0]
        w_item = self.wrap(prevvalue)
        res[0] = w_item
        for index in range(1, length):
            item = storage[index]
            if jit.we_are_jitted() or not self._quick_cmp(item, prevvalue):
                prevvalue = item
                w_item = self.wrap(item)
            res[index] = w_item
        return res

    getitems_unroll = jit.unroll_safe(
            func_with_new_name(getitems_copy, "getitems_unroll"))

    getitems_copy = jit.look_inside_iff(lambda self, w_list:
            w_list._unrolling_heuristic())(getitems_copy)


    @jit.look_inside_iff(lambda self, w_list:
            w_list._unrolling_heuristic())
    def getitems_fixedsize(self, w_list):
        return self.getitems_unroll(w_list)

    def getstorage_copy(self, w_list):
        items = self.unerase(w_list.lstorage)[:]
        return self.erase(items)

    def getslice(self, w_list, start, stop, step, length):
        if step == 1 and 0 <= start <= stop:
            l = self.unerase(w_list.lstorage)
            assert start >= 0
            assert stop >= 0
            sublist = l[start:stop]
            storage = self.erase(sublist)
            return W_ListObject.from_storage_and_strategy(
                    self.space, storage, self, length)
        else:
            subitems_w = [self._none_value] * length
            l = self.unerase(w_list.lstorage)
            self._fill_in_with_sliced_items(subitems_w, l, start, step, length)
            storage = self.erase(subitems_w)
            return W_ListObject.from_storage_and_strategy(
                    self.space, storage, self, length)

    def _fill_in_with_sliced_items(self, subitems_w, l, start, step, length):
        for i in range(length):
            try:
                subitems_w[i] = l[start]
                start += step
            except IndexError:
                raise

    def switch_to_next_strategy(self, w_list, w_sample_item):
        w_list.switch_to_object_strategy()

    def append(self, w_list, w_item):
        if self.is_correct_type(w_item):
            length = w_list.length()
            self._resize_ge(w_list, length + 1)
            self.unerase(w_list.lstorage)[length] = self.unwrap(w_item)
            return

        self.switch_to_next_strategy(w_list, w_item)
        w_list.append(w_item)

    def insert(self, w_list, index, w_item):
        if self.is_correct_type(w_item):
            length = w_list.length()
            self._resize_ge(w_list, length + 1)
            items = self.unerase(w_list.lstorage)
            self._arraymove(items, index, index + 1, length - index)
            items[index] = self.unwrap(w_item)
            return

        self.switch_to_next_strategy(w_list, w_item)
        w_list.insert(index, w_item)

    def _extend_from_list_prefix(self, w_list, other, otherlength):
        length1 = w_list.length()
        try:
            ressize = ovfcheck(length1 + otherlength)
        except OverflowError:
            raise MemoryError
        self._resize_ge(w_list, ressize)
        l = self.unerase(w_list.lstorage)

        self._arraycopy(other, l, 0, length1, otherlength)

    def _extend_from_list(self, w_list, w_other):
        if self.list_is_correct_type(w_other):
            self._extend_from_list_prefix(w_list, self.unerase(w_other.lstorage),
                                          w_other.length())
            return
        elif w_other.strategy.is_empty_strategy():
            return

        w_other = w_other._temporarily_as_objects()
        w_list.switch_to_object_strategy()
        w_list.extend(w_other)

    def setitem(self, w_list, index, w_item):
        l = self.unerase(w_list.lstorage)
        length = w_list.length()
        if r_uint(index) >= r_uint(length):
            index = r_uint(index) + r_uint(length)
            if index >= r_uint(length):
                raise IndexError
            index = intmask(index)

        if self.is_correct_type(w_item):
            l[index] = self.unwrap(w_item)
        else:
            self.switch_to_next_strategy(w_list, w_item)
            w_list.setitem(index, w_item)

    def setslice(self, w_list, start, step, slicelength, w_other):
        assert slicelength >= 0
        space = self.space

        if self is space.fromcache(ObjectListStrategy):
            w_other = w_other._temporarily_as_objects()
        elif not self.list_is_correct_type(w_other) and w_other.length() != 0:
            w_list.switch_to_object_strategy()
            w_other_as_object = w_other._temporarily_as_objects()
            assert (w_other_as_object.strategy is
                    space.fromcache(ObjectListStrategy))
            w_list.setslice(start, step, slicelength, w_other_as_object)
            return

        oldsize = w_list.length()
        len2 = w_other.length()
        if step == 1:  # Support list resizing for non-extended slices
            delta = slicelength - len2
            if delta < 0:
                delta = -delta
                newsize = oldsize + delta
                self._resize_ge(w_list, newsize)
                items = self.unerase(w_list.lstorage)
                self._arraymove(items, start + slicelength, start + len2,
                                oldsize - start - slicelength)
            elif delta == 0:
                pass
            else:
                # start < 0 is only possible with slicelength == 0
                assert start >= 0
                index = start
                items = self.unerase(w_list.lstorage)
                self._arraymove(items, start + delta, start, oldsize - start - delta)
                self._arrayclear(items, oldsize - delta, oldsize)
                self._resize_le(w_list, oldsize - delta)
        elif len2 != slicelength:  # No resize for extended slices
            raise oefmt(space.w_ValueError,
                        "attempt to assign sequence of size %d to extended "
                        "slice of size %d", len2, slicelength)
        items = self.unerase(w_list.lstorage)

        if len2 == 0:
            other_items = []
        else:
            # at this point both w_list and w_other have the same type, so
            # self.unerase is valid for both of them
            other_items = self.unerase(w_other.lstorage)
        if other_items is items:
            if step > 0:
                self._setslice_copy_self_is_other(items, start, step, len2)
                return
            else:
                # other_items is items and step is < 0, therefore:
                assert step == -1
                w_list.reverse()
                return
        if step == 1:
            self._arraycopy(other_items, items, 0, start, len2)
            return

        self._setslice_copy_with_step(items, other_items, start, step, len2)

    def _setslice_copy_with_step(self, items, other_items, start, step, len2):
        for i in range(len2):
            items[start] = other_items[i]
            start += step

    def _setslice_copy_self_is_other(self, items, start, step, len2):
        # Always copy starting from the right to avoid
        # having to make a shallow copy in the case where
        # the source and destination lists are the same list.
        i = len2 - 1
        start += i * step
        while i >= 0:
            items[start] = items[i]
            start -= step
            i -= 1

    def _deleteslice_step(self, items, length, start, step, slicelength):
        # XXX oopspec? unroll?
        i = start
        for discard in range(1, slicelength):
            j = i + 1
            i += step
            while j < i:
                items[j - discard] = items[j]
                j += 1

        j = i + 1
        while j < length:
            items[j - slicelength] = items[j]
            j += 1

    def deleteslice(self, w_list, start, step, slicelength):
        # YYY need test_pypy_c test for not escaping the w_list
        items = self.unerase(w_list.lstorage)
        if slicelength == 0:
            return

        if step < 0:
            start = start + step * (slicelength - 1)
            step = -step

        length = w_list.length()
        if step == 1:
            assert start >= 0
            assert slicelength > 0
            self._arraymove(
                items, start + slicelength, start, length - start - slicelength)
        else:
            self._deleteslice_step(items, length, start, step, slicelength)

        self._arrayclear(items, length - slicelength, length)
        self._resize_le(w_list, length - slicelength)

    def pop_end(self, w_list):
        items = self.unerase(w_list.lstorage)
        length = w_list.length() - 1
        w_res = self.wrap(items[length])
        self._resize_le(w_list, length)
        return w_res

    def pop(self, w_list, index):
        l = self.unerase(w_list.lstorage)
        length = w_list.length()
        if index < 0:
            index += length
        if r_uint(index) >= r_uint(length):
            raise IndexError
        w_res = self.wrap(l[index])
        newlength = length - 1
        self._arraymove(l, index + 1, index, newlength - index)
        if self._need_clearing:
            l[newlength] = self._none_value
        self._resize_le(w_list, newlength)
        return w_res

    def mul(self, w_list, times):
        l = self.unerase(w_list.lstorage)
        rl = wrap_into_resizable_list(l, w_list.length())
        resl = rl * times
        res = resizable_list_extract_storage(resl)
        return W_ListObject.from_storage_and_strategy(
            self.space, self.erase(res), self, len(res))

    def inplace_mul(self, w_list, times):
        if times < 0:
            w_list.clear(self.space)
            return
        # XXX can be done without the extra copy?
        res = self.unerase(w_list.lstorage)[:w_list.length()] * times
        w_list._length *= times
        w_list.lstorage = self.erase(res)

    def reverse(self, w_list):
        length = w_list.length()
        items = self.unerase(w_list.lstorage)
        self._reverse(items, length)

    @staticmethod
    @jit.look_inside_iff(lambda items, length: jit.isvirtual(items) and
                         jit.isconstant(length))
    def _reverse(items, length):
        i = 0
        length_1_i = length - 1 - i
        while i < length_1_i:
            tmp = items[i]
            items[i] = items[length_1_i]
            items[length_1_i] = tmp
            i += 1
            length_1_i -= 1

    def physical_size(self, w_list):
        l = self.unerase(w_list.lstorage)
        return len(l)

    def _unrolling_heuristic(self, w_list):
        storage = self.unerase(w_list.lstorage)
        return jit.loop_unrolling_heuristic(storage, len(storage), UNROLL_CUTOFF)

def _wrap_erase(erase):
    @staticmethod
    def werase(l):
        debug.make_sure_not_resized(l)
        return erase(l)
    return werase

class ObjectListStrategy(ListStrategy):
    import_from_mixin(AbstractUnwrappedStrategy)

    _none_value = None

    def unwrap(self, w_obj):
        return w_obj

    def wrap(self, item):
        return item

    def _quick_cmp(self, a, b):
        return a is b

    erase, unerase = rerased.new_erasing_pair("object")
    erase = _wrap_erase(erase)
    unerase = staticmethod(unerase)

    def getitems_copy(self, w_list):
        storage = self.unerase(w_list.lstorage)
        return storage[:w_list.length()]

    def getitems_unroll(self, w_list):
        storage = self.unerase(w_list.lstorage)
        return storage[:w_list.length()]

    def getitems_fixedsize(self, w_list):
        storage = self.unerase(w_list.lstorage)
        return storage[:w_list.length()]

    def is_correct_type(self, w_obj):
        return True

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(ObjectListStrategy)

    def init_from_list_w(self, w_list, list_w):
        w_list.lstorage = self.erase(resizable_list_extract_storage(list_w))

    def clear(self, w_list):
        w_list._set_length(0)
        w_list.lstorage = self.erase([])

    def find_or_count(self, w_list, w_obj, start, stop, count):
        return ListStrategy.find_or_count(
                self, w_list, w_obj, start, stop, count)

    def getitems(self, w_list):
        l = self.unerase(w_list.lstorage)
        length = w_list.length()
        return wrap_into_resizable_list(l, length)

    # no sort() method here: W_ListObject.descr_sort() handles this
    # case explicitly


class IntegerListStrategy(ListStrategy):
    import_from_mixin(AbstractUnwrappedStrategy)

    _none_value = 0
    _need_clearing = False

    def wrap(self, intval):
        return self.space.newint(intval)

    def unwrap(self, w_int):
        assert type(w_int) is W_IntObject
        return w_int.intval

    def _quick_cmp(self, a, b):
        return a == b

    erase, unerase = rerased.new_erasing_pair("integer")
    erase = _wrap_erase(erase)
    unerase = staticmethod(unerase)

    def is_correct_type(self, w_obj):
        return type(w_obj) is W_IntObject

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(IntegerListStrategy)

    def sort(self, w_list, reverse):
        l = self.unerase(w_list.lstorage)
        sorter = IntSort(l, w_list.length())
        sorter.sort()
        if reverse:
            self.reverse(w_list)

    def getitems_int(self, w_list):
        return self.unerase(w_list.lstorage)[:w_list.length()]


    _base_extend_from_list = _extend_from_list

    def _extend_from_list(self, w_list, w_other):
        if isinstance(w_other.strategy, BaseRangeListStrategy):
            other = resizable_list_extract_storage(w_other.getitems_int())
            assert other is not None
            # XXX could conceivably done more efficiently, unlikely to be worth
            # it
            self._extend_from_list_prefix(w_list, other, len(other))
            return
        if (w_other.strategy is self.space.fromcache(FloatListStrategy) or
            w_other.strategy is self.space.fromcache(IntOrFloatListStrategy)):
            if self.switch_to_int_or_float_strategy(w_list):
                w_list.extend(w_other)
                return
        return self._base_extend_from_list(w_list, w_other)


    _base_setslice = setslice

    def setslice(self, w_list, start, step, slicelength, w_other):
        if w_other.strategy is self.space.fromcache(RangeListStrategy):
            # XXX could conceivably done more efficiently, unlikely to be worth
            # it
            storage = self.erase(resizable_list_extract_storage(w_other.getitems_int()))
            w_other = W_ListObject.from_storage_and_strategy(
                    self.space, storage, self, w_other.length())
        if (w_other.strategy is self.space.fromcache(FloatListStrategy) or
            w_other.strategy is self.space.fromcache(IntOrFloatListStrategy)):
            if self.switch_to_int_or_float_strategy(w_list):
                w_list.setslice(start, step, slicelength, w_other)
                return
        return self._base_setslice(w_list, start, step, slicelength, w_other)


    @staticmethod
    def int_2_float_or_int(w_list):
        l = IntegerListStrategy.unerase(w_list.lstorage)
        length = w_list.length()
        if not longlong2float.CAN_ALWAYS_ENCODE_INT32:
            for index in range(length):
                intval = l[index]
                if not longlong2float.can_encode_int32(intval):
                    raise ValueError
        return [longlong2float.encode_int32_into_longlong_nan(l[index])
                for index in range(length)]

    def switch_to_int_or_float_strategy(self, w_list):
        try:
            generalized_list = self.int_2_float_or_int(w_list)
        except ValueError:
            return False
        strategy = self.space.fromcache(IntOrFloatListStrategy)
        w_list.strategy = strategy
        w_list.lstorage = strategy.erase(generalized_list)
        return True

    def switch_to_next_strategy(self, w_list, w_sample_item):
        if type(w_sample_item) is W_FloatObject:
            if self.switch_to_int_or_float_strategy(w_list):
                # yes, we can switch to IntOrFloatListStrategy
                # (ignore here the extremely unlikely case where
                # w_sample_item is just the wrong nonstandard NaN float;
                # it will caught later and yet another switch will occur)
                return
        # no, fall back to ObjectListStrategy
        w_list.switch_to_object_strategy()

    def repr(self, w_list):
        space = self.space
        length = w_list.length()
        if length == 0:
            return space.newtext('[]')
        builder = StringBuilder(3 * length + 2)
        builder.append('[')
        items = self.unerase(w_list.lstorage)
        for index in range(length):
            if index > 0:
                builder.append(', ')
            value = items[index]
            builder.append(str(value))
        builder.append(']')
        res = builder.build()
        return space.newtext(res)


class FloatListStrategy(ListStrategy):
    import_from_mixin(AbstractUnwrappedStrategy)

    _none_value = 0.0
    _need_clearing = False

    def wrap(self, floatval):
        return self.space.newfloat(floatval)

    def unwrap(self, w_float):
        assert type(w_float) is W_FloatObject
        return w_float.floatval

    erase, unerase = rerased.new_erasing_pair("float")
    erase = _wrap_erase(erase)
    unerase = staticmethod(unerase)

    def _quick_cmp(self, a, b):
        return longlong2float.float2longlong(a) == longlong2float.float2longlong(b)

    def is_correct_type(self, w_obj):
        return type(w_obj) is W_FloatObject

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(FloatListStrategy)

    def sort(self, w_list, reverse):
        l = self.unerase(w_list.lstorage)
        sorter = FloatSort(l, w_list.length())
        sorter.sort()
        if reverse:
            l.reverse()

    def getitems_float(self, w_list):
        return self.unerase(w_list.lstorage)[:w_list.length()]


    _base_extend_from_list = _extend_from_list

    def _extend_from_list(self, w_list, w_other):
        if (w_other.strategy is self.space.fromcache(IntegerListStrategy) or
            w_other.strategy is self.space.fromcache(IntOrFloatListStrategy)):
            # xxx a case that we don't optimize: [3.4].extend([9999999999999])
            # will cause a switch to int-or-float, followed by another
            # switch to object
            if self.switch_to_int_or_float_strategy(w_list):
                w_list.extend(w_other)
                return
        return self._base_extend_from_list(w_list, w_other)


    _base_setslice = setslice

    def setslice(self, w_list, start, step, slicelength, w_other):
        if (w_other.strategy is self.space.fromcache(IntegerListStrategy) or
            w_other.strategy is self.space.fromcache(IntOrFloatListStrategy)):
            if self.switch_to_int_or_float_strategy(w_list):
                w_list.setslice(start, step, slicelength, w_other)
                return
        return self._base_setslice(w_list, start, step, slicelength, w_other)


    def _safe_find_or_count(self, l, length, obj, start, stop, count):
        stop = min(stop, length)
        result = 0
        if not math.isnan(obj):
            for i in range(start, stop):
                val = l[i]
                if val == obj:
                    if count:
                        result += 1
                    else:
                        return i
        else:
            search = longlong2float.float2longlong(obj)
            for i in range(start, stop):
                val = l[i]
                if longlong2float.float2longlong(val) == search:
                    if count:
                        result += 1
                    else:
                        return i
        if count:
            return result
        raise ValueError

    @staticmethod
    def float_2_float_or_int(w_list):
        l = FloatListStrategy.unerase(w_list.lstorage)
        length = w_list.length()
        generalized_list = [IntOrFloatListStrategy._none_value] * length
        for index in range(length):
            floatval = l[index]
            if not longlong2float.can_encode_float(floatval):
                raise ValueError
            generalized_list[index] = (
                longlong2float.float2longlong(floatval))
        return generalized_list

    def switch_to_int_or_float_strategy(self, w_list):
        # xxx we should be able to use the same lstorage, but
        # there is a typing issue (float vs longlong)...
        try:
            generalized_list = self.float_2_float_or_int(w_list)
        except ValueError:
            return False
        strategy = self.space.fromcache(IntOrFloatListStrategy)
        w_list.strategy = strategy
        w_list.lstorage = strategy.erase(generalized_list)
        return True

    def switch_to_next_strategy(self, w_list, w_sample_item):
        if type(w_sample_item) is W_IntObject:
            sample_intval = self.space.int_w(w_sample_item)
            if longlong2float.can_encode_int32(sample_intval):
                if self.switch_to_int_or_float_strategy(w_list):
                    # yes, we can switch to IntOrFloatListStrategy
                    return
        # no, fall back to ObjectListStrategy
        w_list.switch_to_object_strategy()

    def repr(self, w_list):
        from pypy.objspace.std.floatobject import float_repr
        l = self.unerase(w_list.lstorage)
        length = w_list.length()
        if length == 0:
            return self.space.newtext('[]')
        b = StringBuilder()
        b.append('[')
        for i in range(length):
            if i > 0:
                b.append(', ')
            b.append(float_repr(l[i]))
        b.append(']')
        return self.space.newtext(b.build())


class IntOrFloatListStrategy(ListStrategy):
    import_from_mixin(AbstractUnwrappedStrategy)

    _none_value = longlong2float.float2longlong(0.0)
    _need_clearing = False

    def wrap(self, llval):
        if longlong2float.is_int32_from_longlong_nan(llval):
            intval = longlong2float.decode_int32_from_longlong_nan(llval)
            return self.space.newint(intval)
        else:
            floatval = longlong2float.longlong2float(llval)
            return self.space.newfloat(floatval)

    def unwrap(self, w_int_or_float):
        if type(w_int_or_float) is W_IntObject:
            intval = w_int_or_float.intval
            return longlong2float.encode_int32_into_longlong_nan(intval)
        else:
            assert type(w_int_or_float) is W_FloatObject
            floatval = w_int_or_float.floatval
            return longlong2float.float2longlong(floatval)

    def _quick_cmp(self, a, b):
        return a == b

    erase, unerase = rerased.new_erasing_pair("longlong")
    erase = _wrap_erase(erase)
    unerase = staticmethod(unerase)

    def is_correct_type(self, w_obj):
        if type(w_obj) is W_IntObject:
            intval = self.space.int_w(w_obj)
            return longlong2float.can_encode_int32(intval)
        elif type(w_obj) is W_FloatObject:
            floatval = self.space.float_w(w_obj)
            return longlong2float.can_encode_float(floatval)
        else:
            return False

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(IntOrFloatListStrategy)

    def sort(self, w_list, reverse):
        l = self.unerase(w_list.lstorage)
        sorter = IntOrFloatSort(l, w_list.length())
        # Reverse sort stability achieved by initially reversing the list,
        # applying a stable forward sort, then reversing the final result.
        if reverse:
            l.reverse()
        sorter.sort()
        if reverse:
            l.reverse()

    _base_extend_from_list = _extend_from_list

    def _extend_from_list(self, w_list, w_other):
        # XXX what about RangeListStrategy?
        if w_other.strategy is self.space.fromcache(IntegerListStrategy):
            try:
                longlong_list = IntegerListStrategy.int_2_float_or_int(w_other)
            except ValueError:
                pass
            else:
                return self._extend_from_list_prefix(w_list, longlong_list, len(longlong_list))
        if w_other.strategy is self.space.fromcache(FloatListStrategy):
            try:
                longlong_list = FloatListStrategy.float_2_float_or_int(w_other)
            except ValueError:
                pass
            else:
                return self._extend_from_list_prefix(w_list, longlong_list, len(longlong_list))
        return self._base_extend_from_list(w_list, w_other)

    _base_setslice = setslice

    def _temporary_longlong_list(self, longlong_list):
        debug.make_sure_not_resized(longlong_list)
        storage = self.erase(longlong_list)
        return W_ListObject.from_storage_and_strategy(self.space, storage, self, len(longlong_list))

    def setslice(self, w_list, start, step, slicelength, w_other):
        if w_other.strategy is self.space.fromcache(IntegerListStrategy):
            try:
                longlong_list = IntegerListStrategy.int_2_float_or_int(w_other)
            except ValueError:
                pass
            else:
                w_other = self._temporary_longlong_list(longlong_list)
        elif w_other.strategy is self.space.fromcache(FloatListStrategy):
            try:
                longlong_list = FloatListStrategy.float_2_float_or_int(w_other)
            except ValueError:
                pass
            else:
                w_other = self._temporary_longlong_list(longlong_list)
        return self._base_setslice(w_list, start, step, slicelength, w_other)

    def _safe_find_or_count(self, l, length, obj, start, stop, count):
        # careful: we must consider that 0.0 == -0.0 == 0, but also
        # NaN == NaN if they have the same bit pattern.
        fobj = longlong2float.maybe_decode_longlong_as_float(obj)
        result = 0
        for i in range(start, min(stop, length)):
            llval = l[i]
            if llval == obj:     # equal as longlongs: includes NaN == NaN
                if count:
                    result += 1
                    continue
                else:
                    return i
            fval = longlong2float.maybe_decode_longlong_as_float(llval)
            if fval == fobj:     # cases like 0.0 == -0.0 or 42 == 42.0
                if count:
                    result += 1
                else:
                    return i
        if count:
            return result
        raise ValueError

    def repr(self, w_list):
        from pypy.objspace.std.floatobject import float_repr
        l = self.unerase(w_list.lstorage)
        length = w_list.length()
        if len(l) == 0:
            return self.space.newtext('[]')
        b = StringBuilder()
        b.append('[')
        for i in range(length):
            if i > 0:
                b.append(', ')
            llval = l[i]
            if longlong2float.is_int32_from_longlong_nan(llval):
                intval = longlong2float.decode_int32_from_longlong_nan(llval)
                b.append(str(intval))
            else:
                floatval = longlong2float.longlong2float(llval)
                b.append(float_repr(floatval))
        b.append(']')
        return self.space.newtext(b.build())


class BytesListStrategy(ListStrategy):
    import_from_mixin(AbstractUnwrappedStrategy)

    _none_value = ""

    def wrap(self, stringval):
        return self.space.newbytes(stringval)

    def unwrap(self, w_string):
        assert type(w_string) is W_BytesObject
        return w_string._value

    def _quick_cmp(self, a, b):
        return a is b

    erase, unerase = rerased.new_erasing_pair("bytes")
    erase = _wrap_erase(erase)
    unerase = staticmethod(unerase)

    def is_correct_type(self, w_obj):
        return type(w_obj) is W_BytesObject

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(BytesListStrategy)

    def sort(self, w_list, reverse):
        l = self.unerase(w_list.lstorage)
        sorter = StringSort(l, w_list.length())
        sorter.sort()
        if reverse:
            l.reverse()

    def getitems_bytes(self, w_list):
        return self.unerase(w_list.lstorage)[:w_list.length()]


class AsciiListStrategy(ListStrategy):
    import_from_mixin(AbstractUnwrappedStrategy)

    _none_value = ""

    def wrap(self, stringval):
        assert stringval is not None
        return self.space.newutf8(stringval, len(stringval))

    def unwrap(self, w_string):
        assert type(w_string) is W_UnicodeObject
        return w_string._utf8

    def _quick_cmp(self, a, b):
        return a is b

    erase, unerase = rerased.new_erasing_pair("unicode")
    erase = _wrap_erase(erase)
    unerase = staticmethod(unerase)

    def is_correct_type(self, w_obj):
        return type(w_obj) is W_UnicodeObject and w_obj.is_ascii()

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(AsciiListStrategy)

    def sort(self, w_list, reverse):
        l = self.unerase(w_list.lstorage)
        sorter = StringSort(l, w_list.length())
        sorter.sort()
        if reverse:
            l.reverse()

    def getitems_ascii(self, w_list):
        return self.unerase(w_list.lstorage)[:w_list.length()]

# _______________________________________________________

init_signature = Signature(['sequence'], None, None)
init_defaults = [None]


# ____________________________________________________________
# Sorting

# Reverse a slice of a list in place, from lo up to (exclusive) hi.
# (used in sort)

TimSort = make_timsort_class()
IntBaseTimSort = make_timsort_class()
FloatBaseTimSort = make_timsort_class()
IntOrFloatBaseTimSort = make_timsort_class()

# can't use miscutils, because of resizability
StringBaseTimSort = make_timsort_class()

class StringSort(StringBaseTimSort):
    def lt(self, a, b):
        return a < b



class KeyContainer(W_Root):
    def __init__(self, w_key, w_item):
        self.w_key = w_key
        self.w_item = w_item


# NOTE: all the subclasses of TimSort should inherit from a common subclass,
#       so make sure that only SimpleSort inherits directly from TimSort.
#       This is necessary to hide the parent method TimSort.lt() from the
#       annotator.
class SimpleSort(TimSort):
    def lt(self, a, b):
        space = self.space
        return space.is_true(space.lt(a, b))


class IntSort(IntBaseTimSort):
    def lt(self, a, b):
        return a < b


class FloatSort(FloatBaseTimSort):
    def lt(self, a, b):
        return a < b


class IntOrFloatSort(IntOrFloatBaseTimSort):
    def lt(self, a, b):
        fa = longlong2float.maybe_decode_longlong_as_float(a)
        fb = longlong2float.maybe_decode_longlong_as_float(b)
        return fa < fb


class CustomCompareSort(SimpleSort):
    def lt(self, a, b):
        space = self.space
        w_cmp = self.w_cmp
        w_result = space.call_function(w_cmp, a, b)
        try:
            result = space.int_w(w_result)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise oefmt(space.w_TypeError,
                            "comparison function must return int")
            raise
        return result < 0


class CustomKeySort(SimpleSort):
    def lt(self, a, b):
        assert isinstance(a, KeyContainer)
        assert isinstance(b, KeyContainer)
        space = self.space
        return space.is_true(space.lt(a.w_key, b.w_key))


class CustomKeyCompareSort(CustomCompareSort):
    def lt(self, a, b):
        assert isinstance(a, KeyContainer)
        assert isinstance(b, KeyContainer)
        return CustomCompareSort.lt(self, a.w_key, b.w_key)


W_ListObject.typedef = TypeDef("list",
    __doc__ = """list() -> new empty list
list(iterable) -> new list initialized from iterable's items""",
    __new__ = interp2app(W_ListObject.descr_new),
    __init__ = interp2app(W_ListObject.descr_init),
    __repr__ = interp2app(W_ListObject.descr_repr),
    __hash__ = None,

    __eq__ = interp2app(W_ListObject.descr_eq),
    __ne__ = interp2app(W_ListObject.descr_ne),
    __lt__ = interp2app(W_ListObject.descr_lt),
    __le__ = interp2app(W_ListObject.descr_le),
    __gt__ = interp2app(W_ListObject.descr_gt),
    __ge__ = interp2app(W_ListObject.descr_ge),

    __len__ = interp2app(W_ListObject.descr_len),
    __iter__ = interp2app(W_ListObject.descr_iter),
    __contains__ = interp2app(W_ListObject.descr_contains),

    __add__ = interp2app(W_ListObject.descr_add),
    __iadd__ = interp2app(W_ListObject.descr_inplace_add),
    __mul__ = interp2app(W_ListObject.descr_mul),
    __rmul__ = interp2app(W_ListObject.descr_mul),
    __imul__ = interp2app(W_ListObject.descr_inplace_mul),

    __getitem__ = interp2app(W_ListObject.descr_getitem),
    __getslice__ = interp2app(W_ListObject.descr_getslice),
    __setitem__ = interp2app(W_ListObject.descr_setitem),
    __setslice__ = interp2app(W_ListObject.descr_setslice),
    __delitem__ = interp2app(W_ListObject.descr_delitem),
    __delslice__ = interp2app(W_ListObject.descr_delslice),

    sort = interp2app(W_ListObject.descr_sort),
    index = interp2app(W_ListObject.descr_index),
    append = interp2app(W_ListObject.append),
    reverse = interp2app(W_ListObject.descr_reverse),
    __reversed__ = interp2app(W_ListObject.descr_reversed),
    count = interp2app(W_ListObject.descr_count),
    pop = interp2app(W_ListObject.descr_pop),
    extend = interp2app(W_ListObject.extend),
    insert = interp2app(W_ListObject.descr_insert),
    remove = interp2app(W_ListObject.descr_remove),
)
W_ListObject.typedef.flag_sequence_bug_compat = True
