from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.listtype import get_list_index
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype
from pypy.interpreter import gateway, baseobjspace
from pypy.rlib.objectmodel import instantiate, specialize
from pypy.rlib.listsort import make_timsort_class
from pypy.rlib import rerased, jit
from pypy.interpreter.argument import Signature

UNROLL_CUTOFF = 5

def make_range_list(space, start, step, length):
    if length <= 0:
        strategy = space.fromcache(EmptyListStrategy)
        storage = strategy.erase(None)
    else:
        strategy = space.fromcache(RangeListStrategy)
        storage = strategy.erase((start, step, length))
    return W_ListObject.from_storage_and_strategy(space, storage, strategy)

def make_empty_list(space):
    strategy = space.fromcache(EmptyListStrategy)
    storage = strategy.erase(None)
    return W_ListObject.from_storage_and_strategy(space, storage, strategy)

@jit.look_inside_iff(lambda space, list_w: jit.isconstant(len(list_w)) and len(list_w) < UNROLL_CUTOFF)
def get_strategy_from_list_objects(space, list_w):
    if not list_w:
        return space.fromcache(EmptyListStrategy)

    # check for ints
    for w_obj in list_w:
        if not is_W_IntObject(w_obj):
            break
    else:
        return space.fromcache(IntegerListStrategy)

    # check for strings
    for w_obj in list_w:
        if not is_W_StringObject(w_obj):
            break
    else:
        return space.fromcache(StringListStrategy)

    return space.fromcache(ObjectListStrategy)

def is_W_IntObject(w_object):
    from pypy.objspace.std.intobject import W_IntObject
    return type(w_object) is W_IntObject

def is_W_StringObject(w_object):
    from pypy.objspace.std.stringobject import W_StringObject
    return type(w_object) is W_StringObject



class W_ListObject(W_Object):
    from pypy.objspace.std.listtype import list_typedef as typedef

    def __init__(w_self, space, wrappeditems):
        assert isinstance(wrappeditems, list)
        w_self.space = space
        if space.config.objspace.std.withliststrategies:
            w_self.strategy = get_strategy_from_list_objects(space, wrappeditems)
        else:
            w_self.strategy = space.fromcache(ObjectListStrategy)
        w_self.init_from_list_w(wrappeditems)

    @staticmethod
    def from_storage_and_strategy(space, storage, strategy):
        w_self = instantiate(W_ListObject)
        w_self.space = space
        w_self.strategy = strategy
        w_self.lstorage = storage
        if not space.config.objspace.std.withliststrategies:
            w_self.switch_to_object_strategy()
        return w_self

    @staticmethod
    def newlist_str(space, list_s):
        strategy = space.fromcache(StringListStrategy)
        storage = strategy.erase(list_s)
        return W_ListObject.from_storage_and_strategy(space, storage, strategy)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s, %s)" % (w_self.__class__.__name__, w_self.strategy, w_self.lstorage._x)

    def unwrap(w_list, space):
        # for tests only!
        items = [space.unwrap(w_item) for w_item in w_list.getitems()]
        return list(items)

    def switch_to_object_strategy(self):
        list_w = self.getitems()
        self.strategy = self.space.fromcache(ObjectListStrategy)
        # XXX this is quite indirect
        self.init_from_list_w(list_w)

    def _temporarily_as_objects(self):
        if self.strategy is self.space.fromcache(ObjectListStrategy):
            return self
        list_w = self.getitems()
        strategy = self.space.fromcache(ObjectListStrategy)
        storage = strategy.erase(list_w)
        w_objectlist = W_ListObject.from_storage_and_strategy(self.space, storage, strategy)
        return w_objectlist

    # ___________________________________________________

    def init_from_list_w(self, list_w):
        """Initializes listobject by iterating through the given list of
        wrapped items, unwrapping them if neccessary and creating a
        new erased object as storage"""
        self.strategy.init_from_list_w(self, list_w)

    def clone(self):
        """Returns a clone by creating a new listobject
        with the same strategy and a copy of the storage"""
        return self.strategy.clone(self)

    def copy_into(self, other):
        """Used only when extending an EmptyList. Sets the EmptyLists
        strategy and storage according to the other W_List"""
        self.strategy.copy_into(self, other)

    def contains(self, w_obj):
        """Returns unwrapped boolean, saying wether w_obj exists
        in the list."""
        return self.strategy.contains(self, w_obj)

    def append(w_list, w_item):
        """Appends the wrapped item to the end of the list."""
        w_list.strategy.append(w_list, w_item)

    def length(self):
        return self.strategy.length(self)

    def getitem(self, index):
        """Returns the wrapped object that is found in the
        list at the given index. The index must be unwrapped.
        May raise IndexError."""
        return self.strategy.getitem(self, index)

    def getslice(self, start, stop, step, length):
        """Returns a slice of the list defined by the arguments. Arguments must be
        normalized (i.e. using normalize_simple_slice or W_Slice.indices4).
        May raise IndexError."""
        return self.strategy.getslice(self, start, stop, step, length)

    def getitems(self):
        """Returns a list of all items after wrapping them. The result can
        share with the storage, if possible."""
        return self.strategy.getitems(self)

    def getitems_copy(self):
        """Returns a copy of all items in the list. Same as getitems except for
        ObjectListStrategy."""
        return self.strategy.getitems_copy(self)

    def getitems_str(self):
        """ Return the items in the list as unwrapped strings. If the list does
        not use the list strategy, return None. """
        return self.strategy.getitems_str(self)
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

    def extend(self, items_w):
        """Appends the given list of wrapped items."""
        self.strategy.extend(self, items_w)

    def reverse(self):
        """Reverses the list."""
        self.strategy.reverse(self)

    def sort(self, reverse):
        """Sorts the list ascending or descending depending on
        argument reverse. Argument must be unwrapped."""
        self.strategy.sort(self, reverse)

registerimplementation(W_ListObject)


class ListStrategy(object):

    def __init__(self, space):
        self.space = space

    def init_from_list_w(self, w_list, list_w):
        raise NotImplementedError

    def clone(self, w_list):
        raise NotImplementedError

    def copy_into(self, w_list, w_other):
        raise NotImplementedError

    def contains(self, w_list, w_obj):
        # needs to be safe against eq_w() mutating the w_list behind our back
        i = 0
        while i < w_list.length(): # intentionally always calling len!
            if self.space.eq_w(w_list.getitem(i), w_obj):
                return True
            i += 1
        return False

    def length(self, w_list):
        raise NotImplementedError

    def getitem(self, w_list, index):
        raise NotImplementedError

    def getslice(self, w_list, start, stop, step, length):
        raise NotImplementedError

    def getitems(self, w_list):
        return self.getitems_copy(w_list)

    def getitems_copy(self, w_list):
        raise NotImplementedError

    def getitems_str(self, w_list):
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

    def setitem(self, w_list, index, w_item):
        raise NotImplementedError

    def setslice(self, w_list, start, step, slicelength, sequence_w):
        raise NotImplementedError

    def insert(self, w_list, index, w_item):
        raise NotImplementedError

    def extend(self, w_list, items_w):
        raise NotImplementedError

    def reverse(self, w_list):
        raise NotImplementedError

    def sort(self, w_list, reverse):
        raise NotImplementedError

class EmptyListStrategy(ListStrategy):
    """EmptyListStrategy is used when a W_List withouth elements is created.
    The storage is None. When items are added to the W_List a new RPython list
    is created and the strategy and storage of the W_List are changed depending
    to the added item.
    W_Lists do not switch back to EmptyListStrategy when becoming empty again."""

    def __init__(self, space):
        ListStrategy.__init__(self, space)
        # cache an empty list that is used whenever getitems is called (i.e. sorting)
        self.cached_emptylist_w = []

    def init_from_list_w(self, w_list, list_w):
        assert len(list_w) == 0
        w_list.lstorage = self.erase(None)

    erase, unerase = rerased.new_erasing_pair("empty")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def clone(self, w_list):
        return W_ListObject.from_storage_and_strategy(self.space, w_list.lstorage, self)

    def copy_into(self, w_list, w_other):
        pass

    def contains(self, w_list, w_obj):
        return False

    def length(self, w_list):
        return 0

    def getitem(self, w_list, index):
        raise IndexError

    def getslice(self, w_list, start, stop, step, length):
        return W_ListObject(self.space, self.cached_emptylist_w)

    def getitems(self, w_list):
        return self.cached_emptylist_w

    def getitems_copy(self, w_list):
        return []

    def getstorage_copy(self, w_list):
        return self.erase(None)

    def switch_to_correct_strategy(self, w_list, w_item):
        if is_W_IntObject(w_item):
            strategy = self.space.fromcache(IntegerListStrategy)
        elif is_W_StringObject(w_item):
            strategy = self.space.fromcache(StringListStrategy)
        else:
            strategy = self.space.fromcache(ObjectListStrategy)

        storage = strategy.get_empty_storage()
        w_list.strategy = strategy
        w_list.lstorage = storage

    def append(self, w_list, w_item):
        self.switch_to_correct_strategy(w_list, w_item)
        w_list.append(w_item)

    def inplace_mul(self, w_list, times):
        return

    def deleteslice(self, w_list, start, step, slicelength):
        pass

    def pop(self, w_list, index):
        raise IndexError

    def setitem(self, w_list, index, w_item):
        raise IndexError

    def setslice(self, w_list, start, step, slicelength, w_other):
        strategy = w_other.strategy
        storage = strategy.getstorage_copy(w_other)
        w_list.strategy = strategy
        w_list.lstorage = storage

    def sort(self, w_list, reverse):
        return

    def insert(self, w_list, index, w_item):
        assert index == 0
        self.append(w_list, w_item)

    def extend(self, w_list, w_other):
        w_other.copy_into(w_list)

    def reverse(self, w_list):
        pass

class RangeListStrategy(ListStrategy):
    """RangeListStrategy is used when a list is created using the range method.
    The storage is a tuple containing only three integers start, step and length
    and elements are calculated based on these values.
    On any operation destroying the range (inserting, appending non-ints)
    the strategy is switched to IntegerListStrategy."""

    def switch_to_integer_strategy(self, w_list):
        items = self._getitems_range(w_list, False)
        strategy = w_list.strategy = self.space.fromcache(IntegerListStrategy)
        w_list.lstorage = strategy.erase(items)

    def wrap(self, intval):
        return self.space.wrap(intval)

    def unwrap(self, w_int):
        return self.space.int_w(w_int)

    def init_from_list_w(self, w_list, list_w):
        raise NotImplementedError

    erase, unerase = rerased.new_erasing_pair("range")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def clone(self, w_list):
        storage = w_list.lstorage # lstorage is tuple, no need to clone
        w_clone = W_ListObject.from_storage_and_strategy(self.space, storage, self)
        return w_clone

    def copy_into(self, w_list, w_other):
        w_other.strategy = self
        w_other.lstorage = w_list.lstorage

    def contains(self, w_list, w_obj):
        if is_W_IntObject(w_obj):
            start, step, length = self.unerase(w_list.lstorage)
            obj = self.unwrap(w_obj)
            i = start
            if step > 0 and start <= obj <= start + (length - 1) * step and (start - obj) % step == 0:
                return True
            elif step < 0 and start + (length -1) * step <= obj <= start and (start - obj) % step == 0:
                return True
            else:
                return False
        return ListStrategy.contains(self, w_list, w_obj)

    def length(self, w_list):
        return self.unerase(w_list.lstorage)[2]

    def _getitem_unwrapped(self, w_list, i):
        v = self.unerase(w_list.lstorage)
        start = v[0]
        step = v[1]
        length = v[2]
        if i < 0:
            i += length
            if i < 0:
                raise IndexError
        elif i >= length:
            raise IndexError
        return start + i * step

    def getitem(self, w_list, i):
        return self.wrap(self._getitem_unwrapped(w_list, i))

    def getitems_copy(self, w_list):
        return self._getitems_range(w_list, True)

    def getstorage_copy(self, w_list):
        # tuple is unmutable
        return w_list.lstorage


    @specialize.arg(2)
    def _getitems_range(self, w_list, wrap_items):
        l = self.unerase(w_list.lstorage)
        start = l[0]
        step = l[1]
        length  = l[2]
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

    def getslice(self, w_list, start, stop, step, length):
        v = self.unerase(w_list.lstorage)
        old_start = v[0]
        old_step = v[1]
        old_length = v[2]

        new_start = self._getitem_unwrapped(w_list, start)
        new_step = old_step * step
        return make_range_list(self.space, new_start, new_step, length)

    def append(self, w_list, w_item):
        if is_W_IntObject(w_item):
            l = self.unerase(w_list.lstorage)
            step = l[1]
            last_in_range = self._getitem_unwrapped(w_list, -1)
            if self.unwrap(w_item) - step == last_in_range:
                new = self.erase((l[0],l[1],l[2]+1))
                w_list.lstorage = new
                return

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

    def pop(self, w_list, index):
        l = self.unerase(w_list.lstorage)
        start = l[0]
        step = l[1]
        length = l[2]
        if index == 0:
            r = self.getitem(w_list, index)
            new = self.erase((start + step, step, length - 1))
            w_list.lstorage = new
            return r
        elif index == length - 1:
            r = self.getitem(w_list, index)
            new = self.erase((start, step, length - 1))
            w_list.lstorage = new
            return r
        else:
            self.switch_to_integer_strategy(w_list)
            return w_list.pop(index)

    def setitem(self, w_list, index, w_item):
        self.switch_to_integer_strategy(w_list)
        w_list.setitem(index, w_item)

    def setslice(self, w_list, start, step, slicelength, sequence_w):
        self.switch_to_integer_strategy(w_list)
        w_list.setslice(start, step, slicelength, sequence_w)

    def sort(self, w_list, reverse):
        start, step, length = self.unerase(w_list.lstorage)
        if step > 0 and reverse or step < 0 and not reverse:
            start = start + step * (length - 1)
            step = step * (-1)
        else:
            return
        w_list.lstorage = self.erase((start, step, length))

    def insert(self, w_list, index, w_item):
        self.switch_to_integer_strategy(w_list)
        w_list.insert(index, w_item)

    def extend(self, w_list, items_w):
        self.switch_to_integer_strategy(w_list)
        w_list.extend(items_w)

    def reverse(self, w_list):
        v = self.unerase(w_list.lstorage)
        last = self._getitem_unwrapped(w_list, -1)
        length = v[2]
        skip = v[1]
        new = self.erase((last, -skip, length))
        w_list.lstorage = new

class AbstractUnwrappedStrategy(object):
    _mixin_ = True

    def wrap(self, unwrapped):
        raise NotImplementedError

    def unwrap(self, wrapped):
        raise NotImplementedError

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

    @jit.look_inside_iff(lambda space, w_list, list_w:
        jit.isconstant(len(list_w)) and len(list_w) < UNROLL_CUTOFF)
    def init_from_list_w(self, w_list, list_w):
        l = [self.unwrap(w_item) for w_item in list_w]
        w_list.lstorage = self.erase(l)

    def get_empty_storage(self):
        return self.erase([])

    def clone(self, w_list):
        l = self.unerase(w_list.lstorage)
        storage = self.erase(l[:])
        w_clone = W_ListObject.from_storage_and_strategy(self.space, storage, self)
        return w_clone

    def copy_into(self, w_list, w_other):
        w_other.strategy = self
        items = self.unerase(w_list.lstorage)[:]
        w_other.lstorage = self.erase(items)

    def contains(self, w_list, w_obj):
        if self.is_correct_type(w_obj):
            obj = self.unwrap(w_obj)
            l = self.unerase(w_list.lstorage)
            for i in l:
                if i == obj:
                    return True
        return ListStrategy.contains(self, w_list, w_obj)

    def length(self, w_list):
        return len(self.unerase(w_list.lstorage))

    def getitem(self, w_list, index):
        l = self.unerase(w_list.lstorage)
        try:
            r = l[index]
        except IndexError: # make RPython raise the exception
            raise
        return self.wrap(r)

    @jit.look_inside_iff(lambda self, w_list:
            jit.isconstant(w_list.length()) and w_list.length() < UNROLL_CUTOFF)
    def getitems_copy(self, w_list):
        return [self.wrap(item) for item in self.unerase(w_list.lstorage)]

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
            return W_ListObject.from_storage_and_strategy(self.space, storage, self)
        else:
            subitems_w = [self._none_value] * length
            l = self.unerase(w_list.lstorage)
            for i in range(length):
                try:
                    subitems_w[i] = l[start]
                    start += step
                except IndexError:
                    raise
            storage = self.erase(subitems_w)
            return W_ListObject.from_storage_and_strategy(self.space, storage, self)

    def append(self,  w_list, w_item):

        if self.is_correct_type(w_item):
            self.unerase(w_list.lstorage).append(self.unwrap(w_item))
            return

        w_list.switch_to_object_strategy()
        w_list.append(w_item)

    def insert(self, w_list, index, w_item):
        l = self.unerase(w_list.lstorage)

        if self.is_correct_type(w_item):
            l.insert(index, self.unwrap(w_item))
            return

        w_list.switch_to_object_strategy()
        w_list.insert(index, w_item)

    def extend(self, w_list, w_other):
        l = self.unerase(w_list.lstorage)
        if self.list_is_correct_type(w_other):
            l += self.unerase(w_other.lstorage)
            return
        elif w_other.strategy is self.space.fromcache(EmptyListStrategy):
            return

        w_other = w_other._temporarily_as_objects()
        w_list.switch_to_object_strategy()
        w_list.extend(w_other)

    def setitem(self, w_list, index, w_item):
        l = self.unerase(w_list.lstorage)

        if self.is_correct_type(w_item):
            try:
                l[index] = self.unwrap(w_item)
            except IndexError:
                raise
            return

        w_list.switch_to_object_strategy()
        w_list.setitem(index, w_item)

    def setslice(self, w_list, start, step, slicelength, w_other):
        assert slicelength >= 0
        items = self.unerase(w_list.lstorage)

        if self is self.space.fromcache(ObjectListStrategy):
            w_other = w_other._temporarily_as_objects()
        elif (not self.list_is_correct_type(w_other) and
               w_other.length() != 0):
            w_list.switch_to_object_strategy()
            w_other_as_object = w_other._temporarily_as_objects()
            assert w_other_as_object.strategy is self.space.fromcache(ObjectListStrategy)
            w_list.setslice(start, step, slicelength, w_other_as_object)
            return

        oldsize = len(items)
        len2 = w_other.length()
        if step == 1:  # Support list resizing for non-extended slices
            delta = slicelength - len2
            if delta < 0:
                delta = -delta
                newsize = oldsize + delta
                # XXX support this in rlist!
                items += [self._none_value] * delta
                lim = start+len2
                i = newsize - 1
                while i >= lim:
                    items[i] = items[i-delta]
                    i -= 1
            elif start >= 0:
                del items[start:start+delta]
            else:
                assert delta==0   # start<0 is only possible with slicelength==0
        elif len2 != slicelength:  # No resize for extended slices
            raise operationerrfmt(self.space.w_ValueError, "attempt to "
                  "assign sequence of size %d to extended slice of size %d",
                  len2, slicelength)

        if w_other.strategy is self.space.fromcache(EmptyListStrategy):
            other_items = []
        else:
            # at this point both w_list and w_other have the same type, so
            # self.unerase is valid for both of them
            other_items = self.unerase(w_other.lstorage)
        if other_items is items:
            if step > 0:
                # Always copy starting from the right to avoid
                # having to make a shallow copy in the case where
                # the source and destination lists are the same list.
                i = len2 - 1
                start += i*step
                while i >= 0:
                    items[start] = other_items[i]
                    start -= step
                    i -= 1
                return
            else:
                # Make a shallow copy to more easily handle the reversal case
                w_list.reverse()
                return
                #other_items = list(other_items)
        for i in range(len2):
            items[start] = other_items[i]
            start += step

    def deleteslice(self, w_list, start, step, slicelength):
        items = self.unerase(w_list.lstorage)
        if slicelength==0:
            return

        if step < 0:
            start = start + step * (slicelength-1)
            step = -step

        if step == 1:
            assert start >= 0
            assert slicelength >= 0
            del items[start:start+slicelength]
        else:
            n = len(items)
            i = start

            for discard in range(1, slicelength):
                j = i+1
                i += step
                while j < i:
                    items[j-discard] = items[j]
                    j += 1

            j = i+1
            while j < n:
                items[j-slicelength] = items[j]
                j += 1
            start = n - slicelength
            assert start >= 0 # annotator hint
            del items[start:]

    def pop(self, w_list, index):
        l = self.unerase(w_list.lstorage)
        # not sure if RPython raises IndexError on pop
        # so check again here
        if index < 0:
            raise IndexError
        try:
            item = l.pop(index)
        except IndexError:
            raise

        w_item = self.wrap(item)
        return w_item

    def inplace_mul(self, w_list, times):
        l = self.unerase(w_list.lstorage)
        l *= times

    def reverse(self, w_list):
        self.unerase(w_list.lstorage).reverse()

class ObjectListStrategy(AbstractUnwrappedStrategy, ListStrategy):
    _none_value = None

    def unwrap(self, w_obj):
        return w_obj

    def wrap(self, item):
        return item

    erase, unerase = rerased.new_erasing_pair("object")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def is_correct_type(self, w_obj):
        return True

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(ObjectListStrategy)

    def init_from_list_w(self, w_list, list_w):
        w_list.lstorage = self.erase(list_w)

    def contains(self, w_list, w_obj):
        return ListStrategy.contains(self, w_list, w_obj)

    def getitems(self, w_list):
        return self.unerase(w_list.lstorage)

class IntegerListStrategy(AbstractUnwrappedStrategy, ListStrategy):
    _none_value = 0

    def wrap(self, intval):
        return self.space.wrap(intval)

    def unwrap(self, w_int):
        return self.space.int_w(w_int)

    erase, unerase = rerased.new_erasing_pair("integer")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def is_correct_type(self, w_obj):
        return is_W_IntObject(w_obj)

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(IntegerListStrategy)

    def custom_sort_for_ints(self, w_list):
        l = self.unerase(w_list.lstorage)
        self.quicksort(l, 0, len(l) - 1)

    def partition(self, l, start, end):
        left = start
        right = end - 1
        pivot = l[end]

        while left < right:

            while l[left] <= pivot and left < end:
                left += 1

            while l[right] >= pivot and right > start:
                right -= 1

            if left < right:
                l[left], l[right] = l[right], l[left]

        if l[left] > pivot:
            l[left], l[end] = l[end], l[left]

        return left

    def quicksort(self, l, start, end):
        if start < end:
            p = self.partition(l, start, end)
            self.quicksort(l, start, p - 1)
            self.quicksort(l, p + 1, end)

    def sort(self, w_list, reverse):
        l = self.unerase(w_list.lstorage)
        sorter = IntSort(l, len(l))
        sorter.sort()
        if reverse:
            l.reverse()

class StringListStrategy(AbstractUnwrappedStrategy, ListStrategy):
    _none_value = None

    def wrap(self, stringval):
        return self.space.wrap(stringval)

    def unwrap(self, w_string):
        return self.space.str_w(w_string)

    erase, unerase = rerased.new_erasing_pair("string")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def is_correct_type(self, w_obj):
        return is_W_StringObject(w_obj)

    def list_is_correct_type(self, w_list):
        return w_list.strategy is self.space.fromcache(StringListStrategy)

    def sort(self, w_list, reverse):
        l = self.unerase(w_list.lstorage)
        sorter = StringSort(l, len(l))
        sorter.sort()
        if reverse:
            l.reverse()

    def getitems_str(self, w_list):
        return self.unerase(w_list.lstorage)

# _______________________________________________________

init_signature = Signature(['sequence'], None, None)
init_defaults = [None]

def init__List(space, w_list, __args__):
    from pypy.objspace.std.tupleobject import W_TupleObject
    # this is on the silly side
    w_iterable, = __args__.parse_obj(
            None, 'list', init_signature, init_defaults)
    w_list.__init__(space, [])
    if w_iterable is not None:
        # unfortunately this is duplicating space.unpackiterable to avoid
        # assigning a new RPython list to 'wrappeditems', which defeats the
        # W_FastListIterObject optimization.
        if isinstance(w_iterable, W_ListObject):
            w_list.extend(w_iterable)
        elif isinstance(w_iterable, W_TupleObject):
            w_list.extend(W_ListObject(space, w_iterable.wrappeditems[:]))
        else:
            _init_from_iterable(space, w_list, w_iterable)

def _init_from_iterable(space, w_list, w_iterable):
    # in its own function to make the JIT look into init__List
    # XXX this would need a JIT driver somehow?
    w_iterator = space.iter(w_iterable)
    while True:
        try:
            w_item = space.next(w_iterator)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break  # done
        w_list.append(w_item)

def len__List(space, w_list):
    result = w_list.length()
    return wrapint(space, result)

def getitem__List_ANY(space, w_list, w_index):
    try:
        return w_list.getitem(get_list_index(space, w_index))
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))

def getitem__List_Slice(space, w_list, w_slice):
    # XXX consider to extend rlist's functionality?
    length = w_list.length()
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    if slicelength == 0:
        return make_empty_list(space)
    return w_list.getslice(start, stop, step, slicelength)

def getslice__List_ANY_ANY(space, w_list, w_start, w_stop):
    length = w_list.length()
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)

    slicelength = stop - start
    if slicelength == 0:
        return make_empty_list(space)
    return w_list.getslice(start, stop, 1, stop - start)

def setslice__List_ANY_ANY_List(space, w_list, w_start, w_stop, w_other):
    length = w_list.length()
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    w_list.setslice(start, 1, stop-start, w_other)

def setslice__List_ANY_ANY_ANY(space, w_list, w_start, w_stop, w_iterable):
    length = w_list.length()
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    sequence_w = space.listview(w_iterable)
    w_other = W_ListObject(space, sequence_w)
    w_list.setslice(start, 1, stop-start, w_other)

def delslice__List_ANY_ANY(space, w_list, w_start, w_stop):
    length = w_list.length()
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    w_list.deleteslice(start, 1, stop-start)

def contains__List_ANY(space, w_list, w_obj):
    return space.wrap(w_list.contains(w_obj))

def iter__List(space, w_list):
    from pypy.objspace.std import iterobject
    return iterobject.W_FastListIterObject(w_list)

def add__List_List(space, w_list1, w_list2):
    w_clone = w_list1.clone()
    w_clone.extend(w_list2)
    return w_clone

def inplace_add__List_ANY(space, w_list1, w_iterable2):
    try:
        list_extend__List_ANY(space, w_list1, w_iterable2)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    return w_list1

def inplace_add__List_List(space, w_list1, w_list2):
    list_extend__List_List(space, w_list1, w_list2)
    return w_list1

def mul_list_times(space, w_list, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    return w_list.mul(times)

def mul__List_ANY(space, w_list, w_times):
    return mul_list_times(space, w_list, w_times)

def mul__ANY_List(space, w_times, w_list):
    return mul_list_times(space, w_list, w_times)

def inplace_mul__List_ANY(space, w_list, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    w_list.inplace_mul(times)
    return w_list

def eq__List_List(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    if w_list1.length() != w_list2.length():
        return space.w_False

    # XXX in theory, this can be implemented more efficiently as well. let's
    # not care for now
    i = 0
    while i < w_list1.length() and i < w_list2.length():
        if not space.eq_w(w_list1.getitem(i), w_list2.getitem(i)):
            return space.w_False
        i += 1
    return space.w_True

def lessthan_unwrappeditems(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    # XXX in theory, this can be implemented more efficiently as well. let's
    # not care for now
    while i < w_list1.length() and i < w_list2.length():
        w_item1 = w_list1.getitem(i)
        w_item2 = w_list2.getitem(i)
        if not space.eq_w(w_item1, w_item2):
            return space.lt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(w_list1.length() < w_list2.length())

def greaterthan_unwrappeditems(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    # XXX in theory, this can be implemented more efficiently as well. let's
    # not care for now
    while i < w_list1.length() and i < w_list2.length():
        w_item1 = w_list1.getitem(i)
        w_item2 = w_list2.getitem(i)
        if not space.eq_w(w_item1, w_item2):
            return space.gt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(w_list1.length() > w_list2.length())

def lt__List_List(space, w_list1, w_list2):
    return lessthan_unwrappeditems(space, w_list1, w_list2)

def gt__List_List(space, w_list1, w_list2):
    return greaterthan_unwrappeditems(space, w_list1, w_list2)

def delitem__List_ANY(space, w_list, w_idx):
    idx = get_list_index(space, w_idx)
    if idx < 0:
        idx += w_list.length()
    try:
        w_list.pop(idx)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list deletion index out of range"))
    return space.w_None


def delitem__List_Slice(space, w_list, w_slice):
    start, stop, step, slicelength = w_slice.indices4(space, w_list.length())
    w_list.deleteslice(start, step, slicelength)

def setitem__List_ANY_ANY(space, w_list, w_index, w_any):
    idx = get_list_index(space, w_index)
    try:
        w_list.setitem(idx, w_any)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    return space.w_None

def setitem__List_Slice_List(space, w_list, w_slice, w_other):
    oldsize = w_list.length()
    start, stop, step, slicelength = w_slice.indices4(space, oldsize)
    w_list.setslice(start, step, slicelength, w_other)

def setitem__List_Slice_ANY(space, w_list, w_slice, w_iterable):
    oldsize = w_list.length()
    start, stop, step, slicelength = w_slice.indices4(space, oldsize)
    sequence_w = space.listview(w_iterable)
    w_other = W_ListObject(space, sequence_w)
    w_list.setslice(start, step, slicelength, w_other)

app = gateway.applevel("""
    def listrepr(currently_in_repr, l):
        'The app-level part of repr().'
        list_id = id(l)
        if list_id in currently_in_repr:
            return '[...]'
        currently_in_repr[list_id] = 1
        try:
            return "[" + ", ".join([repr(x) for x in l]) + ']'
        finally:
            try:
                del currently_in_repr[list_id]
            except:
                pass
""", filename=__file__)

listrepr = app.interphook("listrepr")

def repr__List(space, w_list):
    if w_list.length() == 0:
        return space.wrap('[]')
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return listrepr(space, w_currently_in_repr, w_list)

def list_insert__List_ANY_ANY(space, w_list, w_where, w_any):
    where = space.int_w(w_where)
    length = w_list.length()
    index = get_positive_index(where, length)
    w_list.insert(index, w_any)
    return space.w_None

def get_positive_index(where, length):
    if where < 0:
        where += length
        if where < 0:
            where = 0
    elif where > length:
        where = length
    assert where >= 0
    return where

def list_append__List_ANY(space, w_list, w_any):
    w_list.append(w_any)
    return space.w_None

def list_extend__List_List(space, w_list, w_other):
    w_list.extend(w_other)
    return space.w_None

def list_extend__List_ANY(space, w_list, w_any):
    w_other = W_ListObject(space, space.listview(w_any))
    w_list.extend(w_other)
    return space.w_None

# note that the default value will come back wrapped!!!
def list_pop__List_ANY(space, w_list, w_idx=-1):
    length = w_list.length()
    if length == 0:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop from empty list"))
    if space.isinstance_w(w_idx, space.w_float):
        raise OperationError(space.w_TypeError,
            space.wrap("integer argument expected, got float")
        )
    idx = space.int_w(space.int(w_idx))
    if idx < 0:
        idx += length
    try:
        return w_list.pop(idx)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop index out of range"))

def list_remove__List_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    i = 0
    while i < w_list.length():
        if space.eq_w(w_list.getitem(i), w_any):
            if i < w_list.length(): # if this is wrong the list was changed
                w_list.pop(i)
            return space.w_None
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.remove(x): x not in list"))

def list_index__List_ANY_ANY_ANY(space, w_list, w_any, w_start, w_stop):
    # needs to be safe against eq_w() mutating the w_list behind our back
    size = w_list.length()
    i = slicetype.adapt_bound(space, size, w_start)
    stop = slicetype.adapt_bound(space, size, w_stop)
    while i < stop and i < w_list.length():
        if space.eq_w(w_list.getitem(i), w_any):
            return space.wrap(i)
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.index(x): x not in list"))

def list_count__List_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    count = 0
    i = 0
    while i < w_list.length():
        if space.eq_w(w_list.getitem(i), w_any):
            count += 1
        i += 1
    return space.wrap(count)

def list_reverse__List(space, w_list):
    w_list.reverse()
    return space.w_None

# ____________________________________________________________
# Sorting

# Reverse a slice of a list in place, from lo up to (exclusive) hi.
# (used in sort)

TimSort = make_timsort_class()
IntBaseTimSort = make_timsort_class()
StringBaseTimSort = make_timsort_class()

class KeyContainer(baseobjspace.W_Root):
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

class StringSort(StringBaseTimSort):
    def lt(self, a, b):
        return a < b

class CustomCompareSort(SimpleSort):
    def lt(self, a, b):
        space = self.space
        w_cmp = self.w_cmp
        w_result = space.call_function(w_cmp, a, b)
        try:
            result = space.int_w(w_result)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                raise OperationError(space.w_TypeError,
                    space.wrap("comparison function must return int"))
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

def list_sort__List_ANY_ANY_ANY(space, w_list, w_cmp, w_keyfunc, w_reverse):

    has_cmp = not space.is_w(w_cmp, space.w_None)
    has_key = not space.is_w(w_keyfunc, space.w_None)
    has_reverse = space.is_true(w_reverse)

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
            if w_list.strategy is space.fromcache(ObjectListStrategy):
                sorterclass = SimpleSort
            else:
                w_list.sort(has_reverse)
                return space.w_None

    sorter = sorterclass(w_list.getitems(), w_list.length())
    sorter.space = space
    sorter.w_cmp = w_cmp

    try:
        # The list is temporarily made empty, so that mutations performed
        # by comparison functions can't affect the slice of memory we're
        # sorting (allowing mutations during sorting is an IndexError or
        # core-dump factory, since the storage may change).
        w_list.__init__(space, [])

        # wrap each item in a KeyContainer if needed
        if has_key:
            for i in range(sorter.listlength):
                w_item = sorter.list[i]
                w_key = space.call_function(w_keyfunc, w_item)
                sorter.list[i] = KeyContainer(w_key, w_item)

        # Reverse sort stability achieved by initially reversing the list,
        # applying a stable forward sort, then reversing the final result.
        if has_reverse:
            sorter.list.reverse()

        # perform the sort
        sorter.sort()

        # reverse again
        if has_reverse:
            sorter.list.reverse()

    finally:
        # unwrap each item if needed
        if has_key:
            for i in range(sorter.listlength):
                w_obj = sorter.list[i]
                if isinstance(w_obj, KeyContainer):
                    sorter.list[i] = w_obj.w_item

        # check if the user mucked with the list during the sort
        mucked = w_list.length() > 0

        # put the items back into the list
        w_list.__init__(space, sorter.list)

    if mucked:
        raise OperationError(space.w_ValueError,
                             space.wrap("list modified during sort"))

    return space.w_None


from pypy.objspace.std import listtype
register_all(vars(), listtype)
