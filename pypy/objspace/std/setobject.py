from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.rlib.objectmodel import r_dict
from pypy.rlib.rarithmetic import intmask, r_uint
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.interpreter.argument import Signature
from pypy.objspace.std.settype import set_typedef as settypedef
from pypy.objspace.std.frozensettype import frozenset_typedef as frozensettypedef
from pypy.rlib import rerased
from pypy.rlib.objectmodel import instantiate
from pypy.interpreter.generator import GeneratorIterator
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.intobject import W_IntObject

class W_BaseSetObject(W_Object):
    typedef = None

    # make sure that Base is used for Set and Frozenset in multimethod
    # declarations
    @classmethod
    def is_implementation_for(cls, typedef):
        if typedef is frozensettypedef or typedef is settypedef:
            assert cls is W_BaseSetObject
            return True
        return False

    def __init__(w_self, space, w_iterable=None):
        """Initialize the set by taking ownership of 'setdata'."""
        w_self.space = space
        set_strategy_and_setdata(space, w_self, w_iterable)

    def __repr__(w_self):
        """representation for debugging purposes"""
        reprlist = [repr(w_item) for w_item in w_self.getkeys()]
        return "<%s(%s)>" % (w_self.__class__.__name__, ', '.join(reprlist))

    def from_storage_and_strategy(w_self, storage, strategy):
        obj = w_self._newobj(w_self.space, None)
        assert isinstance(obj, W_BaseSetObject)
        obj.strategy = strategy
        obj.sstorage = storage
        return obj

    _lifeline_ = None
    def getweakref(self):
        return self._lifeline_

    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline
    def delweakref(self):
        self._lifeline_ = None

    def switch_to_object_strategy(self, space):
        d = self.strategy.getdict_w(self)
        self.strategy = strategy = space.fromcache(ObjectSetStrategy)
        self.sstorage = strategy.erase(d)

    def switch_to_empty_strategy(self):
        self.strategy = strategy = self.space.fromcache(EmptySetStrategy)
        self.sstorage = strategy.get_empty_storage()

    # _____________ strategy methods ________________

    def clear(self):
        """ Removes all elements from the set. """
        self.strategy.clear(self)

    def copy(self):
        """ Returns a clone of the set. """
        return self.strategy.copy(self)

    def length(self):
        """ Returns the number of items inside the set. """
        return self.strategy.length(self)

    def add(self, w_key):
        """ Adds an element to the set. The element must be wrapped. """
        self.strategy.add(self, w_key)

    def remove(self, w_item):
        """ Removes the given element from the set. Element must be wrapped. """
        return self.strategy.remove(self, w_item)

    def getdict_w(self):
        """ Returns a dict with all elements of the set. Needed only for switching to ObjectSetStrategy. """
        return self.strategy.getdict_w(self)

    def get_storage_copy(self):
        """ Returns a copy of the storage. Needed when we want to clone all elements from one set and
        put them into another. """
        return self.strategy.get_storage_copy(self)

    def getkeys(self):
        """ Returns a list of all elements inside the set. Only used in __repr__. Use as less as possible."""
        return self.strategy.getkeys(self)

    def difference(self, w_other):
        """ Returns a set with all items that are in this set, but not in w_other. W_other must be a set."""
        return self.strategy.difference(self, w_other)

    def difference_update(self, w_other):
        """ As difference but overwrites the sets content with the result. """
        return self.strategy.difference_update(self, w_other)

    def symmetric_difference(self, w_other):
        """ Returns a set with all items that are either in this set or in w_other, but not in both. W_other must be a set. """
        return self.strategy.symmetric_difference(self, w_other)

    def symmetric_difference_update(self, w_other):
        """ As symmetric_difference but overwrites the content of the set with the result. """
        return self.strategy.symmetric_difference_update(self, w_other)

    def intersect(self, w_other):
        """ Returns a set with all items that exists in both sets, this set and in w_other. W_other must be a set. """
        return self.strategy.intersect(self, w_other)

    def intersect_update(self, w_other):
        """ Keeps only those elements found in both sets, removing all other elements. """
        return self.strategy.intersect_update(self, w_other)

    def intersect_multiple(self, others_w):
        """ Returns a new set of all elements that exist in all of the given iterables."""
        return self.strategy.intersect_multiple(self, others_w)

    def intersect_multiple_update(self, others_w):
        """ Same as intersect_multiple but overwrites this set with the result. """
        self.strategy.intersect_multiple_update(self, others_w)

    def issubset(self, w_other):
        """ Checks wether this set is a subset of w_other. W_other must be a set. """
        return self.strategy.issubset(self, w_other)

    def isdisjoint(self, w_other):
        """ Checks wether this set and the w_other are completly different, i.e. have no equal elements. """
        return self.strategy.isdisjoint(self, w_other)

    def update(self, w_other):
        """ Appends all elements from the given set to this set. """
        self.strategy.update(self, w_other)

    def has_key(self, w_key):
        """ Checks wether this set contains the given wrapped key."""
        return self.strategy.has_key(self, w_key)

    def equals(self, w_other):
        """ Checks wether this set and the given set are equal, i.e. contain the same elements. """
        return self.strategy.equals(self, w_other)

    def iter(self):
        """ Returns an iterator of the elements from this set. """
        return self.strategy.iter(self)

    def popitem(self):
        """ Removes an arbitrary element from the set. May raise KeyError if set is empty."""
        return self.strategy.popitem(self)

class W_SetObject(W_BaseSetObject):
    from pypy.objspace.std.settype import set_typedef as typedef

    def _newobj(w_self, space, rdict_w):
        """Make a new set by taking ownership of 'rdict_w'."""
        if type(w_self) is W_SetObject:
            return W_SetObject(space, rdict_w)
        w_type = space.type(w_self)
        w_obj = space.allocate_instance(W_SetObject, w_type)
        W_SetObject.__init__(w_obj, space, rdict_w)
        return w_obj

class W_FrozensetObject(W_BaseSetObject):
    from pypy.objspace.std.frozensettype import frozenset_typedef as typedef
    hash = 0

    def _newobj(w_self, space, rdict_w):
        """Make a new frozenset by taking ownership of 'rdict_w'."""
        if type(w_self) is W_FrozensetObject:
            return W_FrozensetObject(space, rdict_w)
        w_type = space.type(w_self)
        w_obj = space.allocate_instance(W_FrozensetObject, w_type)
        W_FrozensetObject.__init__(w_obj, space, rdict_w)
        return w_obj

registerimplementation(W_BaseSetObject)
registerimplementation(W_SetObject)
registerimplementation(W_FrozensetObject)

class SetStrategy(object):
    def __init__(self, space):
        self.space = space

    def get_empty_dict(self):
        """ Returns an empty dictionary depending on the strategy. Used to initalize a new storage. """
        raise NotImplementedError

    def get_empty_storage(self):
        """ Returns an empty storage (erased) object. Used to initialize an empty set."""
        raise NotImplementedError

    #def erase(self, storage):
    #    raise NotImplementedError

    #def unerase(self, storage):
    #    raise NotImplementedError

    # __________________ methods called on W_SetObject _________________

    def clear(self, w_set):
        raise NotImplementedError

    def copy(self, w_set):
        raise NotImplementedError

    def length(self, w_set):
        raise NotImplementedError

    def add(self, w_set, w_key):
        raise NotImplementedError

    def remove(self, w_set, w_item):
        raise NotImplementedError

    def getdict_w(self, w_set):
        raise NotImplementedError

    def get_storage_copy(self, w_set):
        raise NotImplementedError

    def getkeys(self, w_set):
        raise NotImplementedError

    def difference(self, w_set, w_other):
        raise NotImplementedError

    def difference_update(self, w_set, w_other):
        raise NotImplementedError

    def symmetric_difference(self, w_set, w_other):
        raise NotImplementedError

    def symmetric_difference_update(self, w_set, w_other):
        raise NotImplementedError

    def intersect(self, w_set, w_other):
        raise NotImplementedError

    def intersect_update(self, w_set, w_other):
        raise NotImplementedError

    def intersect_multiple(self, w_set, others_w):
        raise NotImplementedError

    def intersect_multiple_update(self, w_set, others_w):
        raise NotImplementedError

    def issubset(self, w_set, w_other):
        raise NotImplementedError

    def isdisjoint(self, w_set, w_other):
        raise NotImplementedError

    def update(self, w_set, w_other):
        raise NotImplementedError

    def has_key(self, w_set, w_key):
        raise NotImplementedError

    def equals(self, w_set, w_other):
        raise NotImplementedError

    def iter(self, w_set):
        raise NotImplementedError

    def popitem(self, w_set):
        raise NotImplementedError

class EmptySetStrategy(SetStrategy):

    erase, unerase = rerased.new_erasing_pair("empty")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def check_for_unhashable_objects(self, w_iterable):
        w_iterator = self.space.iter(w_iterable)
        while True:
            try:
                elem = self.space.next(w_iterator)
                self.space.hash(elem)
            except OperationError, e:
                if not e.match(self.space, self.space.w_StopIteration):
                    raise
                break

    def get_empty_storage(self):
        return self.erase(None)

    def is_correct_type(self, w_key):
        return False

    def length(self, w_set):
        return 0

    def clear(self, w_set):
        pass

    def copy(self, w_set):
        storage = self.erase(None)
        clone = w_set.from_storage_and_strategy(storage, self)
        return clone

    def add(self, w_set, w_key):
        if type(w_key) is W_IntObject:
            strategy = self.space.fromcache(IntegerSetStrategy)
        else:
            strategy = self.space.fromcache(ObjectSetStrategy)
        w_set.strategy = strategy
        w_set.sstorage = strategy.get_empty_storage()
        w_set.add(w_key)

    def remove(self, w_set, w_item):
        return False

    def discard(self, w_set, w_item):
        return False

    def getdict_w(self, w_set):
        return newset(self.space)

    def get_storage_copy(self, w_set):
        return w_set.sstorage

    def getkeys(self, w_set):
        return []

    def has_key(self, w_set, w_key):
        return False

    def equals(self, w_set, w_other):
        if w_other.strategy is self or w_other.length() == 0:
            return True
        return False

    def difference(self, w_set, w_other):
        return w_set.copy()

    def difference_update(self, w_set, w_other):
        self.check_for_unhashable_objects(w_other)

    def intersect(self, w_set, w_other):
        self.check_for_unhashable_objects(w_other)
        return w_set.copy()

    def intersect_update(self, w_set, w_other):
        self.check_for_unhashable_objects(w_other)
        return w_set.copy()

    def intersect_multiple(self, w_set, others_w):
        self.intersect_multiple_update(w_set, others_w)
        return w_set.copy()

    def intersect_multiple_update(self, w_set, others_w):
        for w_other in others_w:
            self.intersect(w_set, w_other)

    def isdisjoint(self, w_set, w_other):
        return True

    def issubset(self, w_set, w_other):
        return True

    def symmetric_difference(self, w_set, w_other):
        return w_other.copy()

    def symmetric_difference_update(self, w_set, w_other):
        w_set.strategy = w_other.strategy
        w_set.sstorage = w_other.get_storage_copy()

    def update(self, w_set, w_other):
        w_set.strategy = w_other.strategy
        w_set.sstorage = w_other.get_storage_copy()

    def iter(self, w_set):
        return EmptyIteratorImplementation(self.space, w_set)

    def popitem(self, w_set):
        raise OperationError(self.space.w_KeyError,
                                self.space.wrap('pop from an empty set'))

class AbstractUnwrappedSetStrategy(object):
    _mixin_ = True

    def is_correct_type(self, w_key):
        """ Checks wether the given wrapped key fits this strategy."""
        raise NotImplementedError

    def unwrap(self, w_item):
        """ Returns the unwrapped value of the given wrapped item."""
        raise NotImplementedError

    def wrap(self, item):
        """ Returns a wrapped version of the given unwrapped item. """
        raise NotImplementedError

    def get_storage_from_list(self, list_w):
        setdata = self.get_empty_dict()
        for w_item in list_w:
            setdata[self.unwrap(w_item)] = None
        return self.erase(setdata)

    def length(self, w_set):
        return len(self.unerase(w_set.sstorage))

    def clear(self, w_set):
        w_set.switch_to_empty_strategy()

    def copy(self, w_set):
        strategy = w_set.strategy
        if isinstance(w_set, W_FrozensetObject):
            storage = w_set.sstorage
        else:
            d = self.unerase(w_set.sstorage)
            storage = self.erase(d.copy())
        clone = w_set.from_storage_and_strategy(storage, strategy)
        return clone

    def add(self, w_set, w_key):
        if self.is_correct_type(w_key):
            d = self.unerase(w_set.sstorage)
            d[self.unwrap(w_key)] = None
        else:
            w_set.switch_to_object_strategy(self.space)
            w_set.add(w_key)

    def remove(self, w_set, w_item):
        from pypy.objspace.std.dictmultiobject import _never_equal_to_string
        d = self.unerase(w_set.sstorage)
        if not self.is_correct_type(w_item):
            #XXX check type of w_item and immediately return False in some cases
            w_set.switch_to_object_strategy(self.space)
            return w_set.remove(w_item)

        key = self.unwrap(w_item)
        try:
            del d[key]
            return True
        except KeyError:
            return False

    def getdict_w(self, w_set):
        result = newset(self.space)
        keys = self.unerase(w_set.sstorage).keys()
        for key in keys:
            result[self.wrap(key)] = None
        return result

    def get_storage_copy(self, w_set):
        d = self.unerase(w_set.sstorage)
        copy = self.erase(d.copy())
        return copy

    def getkeys(self, w_set):
        keys = self.unerase(w_set.sstorage).keys()
        keys_w = [self.wrap(key) for key in keys]
        return keys_w

    def has_key(self, w_set, w_key):
        from pypy.objspace.std.dictmultiobject import _never_equal_to_string
        if not self.is_correct_type(w_key):
            #XXX check type of w_item and immediately return False in some cases
            w_set.switch_to_object_strategy(self.space)
            return w_set.has_key(w_key)
        d = self.unerase(w_set.sstorage)
        return self.unwrap(w_key) in d

    def equals(self, w_set, w_other):
        if w_set.length() != w_other.length():
            return False
        items = self.unerase(w_set.sstorage).keys()
        for key in items:
            if not w_other.has_key(self.wrap(key)):
                return False
        return True

    def _difference_wrapped(self, w_set, w_other):
        strategy = self.space.fromcache(ObjectSetStrategy)

        d_new = strategy.get_empty_dict()
        for obj in self.unerase(w_set.sstorage):
            w_item = self.wrap(obj)
            if not w_other.has_key(w_item):
                d_new[w_item] = None

        return strategy.erase(d_new)

    def _difference_unwrapped(self, w_set, w_other):
        iterator = self.unerase(w_set.sstorage).iterkeys()
        other_dict = self.unerase(w_other.sstorage)
        result_dict = self.get_empty_dict()
        for key in iterator:
            if key not in other_dict:
                result_dict[key] = None
        return self.erase(result_dict)

    def _difference_base(self, w_set, w_other):
        if not isinstance(w_other, W_BaseSetObject):
            w_other = w_set._newobj(self.space, w_other)

        if self is w_other.strategy:
            strategy = w_set.strategy
            storage = self._difference_unwrapped(w_set, w_other)
        else:
            strategy = self.space.fromcache(ObjectSetStrategy)
            storage = self._difference_wrapped(w_set, w_other)
        return storage, strategy

    def difference(self, w_set, w_other):
        #XXX return clone for ANY with Empty (and later different strategies)
        storage, strategy = self._difference_base(w_set, w_other)
        w_newset = w_set.from_storage_and_strategy(storage, strategy)
        return w_newset

    def difference_update(self, w_set, w_other):
        #XXX do nothing for ANY with Empty
        storage, strategy = self._difference_base(w_set, w_other)
        w_set.strategy = strategy
        w_set.sstorage = storage

    def _symmetric_difference_unwrapped(self, w_set, w_other):
        d_new = self.get_empty_dict()
        d_this = self.unerase(w_set.sstorage)
        d_other = self.unerase(w_other.sstorage)
        for key in d_other.keys():
            if not key in d_this:
                d_new[key] = None
        for key in d_this.keys():
            if not key in d_other:
                d_new[key] = None

        storage = self.erase(d_new)
        return storage

    def _symmetric_difference_wrapped(self, w_set, w_other):
        newsetdata = newset(self.space)
        for obj in self.unerase(w_set.sstorage):
            w_item = self.wrap(obj)
            if not w_other.has_key(w_item):
                newsetdata[w_item] = None

        w_iterator = w_other.iter()
        while True:
            w_item = w_iterator.next_entry()
            if w_item is None:
                break
            if not w_set.has_key(w_item):
                newsetdata[w_item] = None

        strategy = self.space.fromcache(ObjectSetStrategy)
        return strategy.erase(newsetdata)

    def _symmetric_difference_base(self, w_set, w_other):
        if self is w_other.strategy:
            strategy = w_set.strategy
            storage = self._symmetric_difference_unwrapped(w_set, w_other)
        else:
            strategy = self.space.fromcache(ObjectSetStrategy)
            storage = self._symmetric_difference_wrapped(w_set, w_other)
        return storage, strategy

    def symmetric_difference(self, w_set, w_other):
        storage, strategy = self._symmetric_difference_base(w_set, w_other)
        return w_set.from_storage_and_strategy(storage, strategy)

    def symmetric_difference_update(self, w_set, w_other):
        storage, strategy = self._symmetric_difference_base(w_set, w_other)
        w_set.strategy = strategy
        w_set.sstorage = storage

    def _intersect_base(self, w_set, w_other):
        if self is w_other.strategy:
            strategy = w_set.strategy
            storage = strategy._intersect_unwrapped(w_set, w_other)
        else:
            strategy = self.space.fromcache(ObjectSetStrategy)
            storage = strategy._intersect_wrapped(w_set, w_other)
        return storage, strategy

    def _intersect_wrapped(self, w_set, w_other):
        result = self.get_empty_dict()
        items = self.unerase(w_set.sstorage).iterkeys()
        for key in items:
            w_key = self.wrap(key)
            if w_other.has_key(w_key):
                result[w_key] = None
        return self.erase(result)

    def _intersect_unwrapped(self, w_set, w_other):
        result = self.get_empty_dict()
        d_this = self.unerase(w_set.sstorage)
        d_other = self.unerase(w_other.sstorage)
        for key in d_this:
            if key in d_other:
                result[key] = None
        return self.erase(result)

    def intersect(self, w_set, w_other):
        if w_set.length() > w_other.length():
            return w_other.intersect(w_set)

        storage, strategy = self._intersect_base(w_set, w_other)
        return w_set.from_storage_and_strategy(storage, strategy)

    def intersect_update(self, w_set, w_other):
        if w_set.length() > w_other.length():
            w_intersection = w_other.intersect(w_set)
            strategy = w_intersection.strategy
            storage = w_intersection.sstorage
        else:
            storage, strategy = self._intersect_base(w_set, w_other)
        w_set.strategy = strategy
        w_set.sstorage = storage
        return w_set

    def intersect_multiple(self, w_set, others_w):
        #XXX find smarter implementations
        result = w_set.copy()
        for w_other in others_w:
            if isinstance(w_other, W_BaseSetObject):
                # optimization only
                result.intersect_update(w_other)
            else:
                w_other_as_set = w_set._newobj(self.space, w_other)
                result.intersect_update(w_other_as_set)
        return result

    def intersect_multiple_update(self, w_set, others_w):
        result = self.intersect_multiple(w_set, others_w)
        w_set.strategy = result.strategy
        w_set.sstorage = result.sstorage

    def _issubset_unwrapped(self, w_set, w_other):
        d_other = self.unerase(w_other.sstorage)
        for item in self.unerase(w_set.sstorage):
            if not item in d_other:
                return False
        return True

    def _issubset_wrapped(self, w_set, w_other):
        for obj in self.unerase(w_set.sstorage):
            w_item = self.wrap(obj)
            if not w_other.has_key(w_item):
                return False
        return True

    def issubset(self, w_set, w_other):
        if w_set.length() == 0:
            return True

        if w_set.strategy is w_other.strategy:
            return self._issubset_unwrapped(w_set, w_other)
        else:
            return self._issubset_wrapped(w_set, w_other)

    def _isdisjoint_unwrapped(self, w_set, w_other):
        d_set = self.unerase(w_set.sstorage)
        d_other = self.unerase(w_other.sstorage)
        for key in d_set:
            if key in d_other:
                return False
        return True

    def _isdisjoint_wrapped(w_set, w_other):
        d = self.unerase(w_set.sstorage)
        for key in d:
            if w_other.has_key(self.wrap(key)):
                return False
        return True

    def isdisjoint(self, w_set, w_other):
        if w_other.length() == 0:
            return True
        if w_set.length() > w_other.length():
            return w_other.isdisjoint(w_set)

        if w_set.strategy is w_other.strategy:
            return self._isdisjoint_unwrapped(w_set, w_other)
        else:
            return self._isdisjoint_wrapped(w_set, w_other)

    def update(self, w_set, w_other):
        if self is w_other.strategy:
            d_set = self.unerase(w_set.sstorage)
            d_other = self.unerase(w_other.sstorage)
            d_set.update(d_other)
            return

        w_set.switch_to_object_strategy(self.space)
        w_set.update(w_other)

    def popitem(self, w_set):
        storage = self.unerase(w_set.sstorage)
        try:
            # this returns a tuple because internally sets are dicts
            result = storage.popitem()
        except KeyError:
            # strategy may still be the same even if dict is empty
            raise OperationError(self.space.w_KeyError,
                            self.space.wrap('pop from an empty set'))
        return self.wrap(result[0])

class IntegerSetStrategy(AbstractUnwrappedSetStrategy, SetStrategy):
    erase, unerase = rerased.new_erasing_pair("integer")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def get_empty_storage(self):
        return self.erase({})

    def get_empty_dict(self):
        return {}

    def is_correct_type(self, w_key):
        from pypy.objspace.std.intobject import W_IntObject
        return type(w_key) is W_IntObject

    def unwrap(self, w_item):
        return self.space.int_w(w_item)

    def wrap(self, item):
        return self.space.wrap(item)

    def iter(self, w_set):
        return IntegerIteratorImplementation(self.space, self, w_set)

class ObjectSetStrategy(AbstractUnwrappedSetStrategy, SetStrategy):
    erase, unerase = rerased.new_erasing_pair("object")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def get_empty_storage(self):
        return self.erase(self.get_empty_dict())

    def get_empty_dict(self):
        return newset(self.space)

    def is_correct_type(self, w_key):
        return True

    def unwrap(self, w_item):
        return w_item

    def wrap(self, item):
        return item

    def iter(self, w_set):
        return RDictIteratorImplementation(self.space, self, w_set)

    def update(self, w_set, w_other):
        d_obj = self.unerase(w_set.sstorage)
        w_iterator = w_other.iter()
        while True:
            w_item = w_iterator.next_entry()
            if w_item is None:
                break
            d_obj[w_item] = None

class IteratorImplementation(object):
    def __init__(self, space, implementation):
        self.space = space
        self.setimplementation = implementation
        self.len = implementation.length()
        self.pos = 0

    def next(self):
        if self.setimplementation is None:
            return None
        if self.len != self.setimplementation.length():
            self.len = -1   # Make this error state sticky
            raise OperationError(self.space.w_RuntimeError,
                     self.space.wrap("set changed size during iteration"))
        # look for the next entry
        if self.pos < self.len:
            result = self.next_entry()
            self.pos += 1
            return result
        # no more entries
        self.setimplementation = None
        return None

    def next_entry(self):
        """ Purely abstract method
        """
        raise NotImplementedError

    def length(self):
        if self.setimplementation is not None:
            return self.len - self.pos
        return 0

class EmptyIteratorImplementation(IteratorImplementation):
    def next_entry(self):
        return None

class IntegerIteratorImplementation(IteratorImplementation):
    #XXX same implementation in dictmultiobject on dictstrategy-branch
    def __init__(self, space, strategy, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        d = strategy.unerase(dictimplementation.sstorage)
        self.iterator = d.iterkeys()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for key in self.iterator:
            return self.space.wrap(key)
        else:
            return None

class RDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, strategy, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        d = strategy.unerase(dictimplementation.sstorage)
        self.iterator = d.iterkeys()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for w_key in self.iterator:
            return w_key
        else:
            return None

class W_SetIterObject(W_Object):
    from pypy.objspace.std.settype import setiter_typedef as typedef

    def __init__(w_self, space, iterimplementation):
        w_self.space = space
        w_self.iterimplementation = iterimplementation

registerimplementation(W_SetIterObject)

def iter__SetIterObject(space, w_setiter):
    return w_setiter

def next__SetIterObject(space, w_setiter):
    iterimplementation = w_setiter.iterimplementation
    w_key = iterimplementation.next()
    if w_key is not None:
        return w_key
    raise OperationError(space.w_StopIteration, space.w_None)

# XXX __length_hint__()
##def len__SetIterObject(space, w_setiter):
##    content = w_setiter.content
##    if content is None or w_setiter.len == -1:
##        return space.wrap(0)
##    return space.wrap(w_setiter.len - w_setiter.pos)

# some helper functions

def newset(space):
    return r_dict(space.eq_w, space.hash_w, force_non_null=True)

def set_strategy_and_setdata(space, w_set, w_iterable):
    from pypy.objspace.std.intobject import W_IntObject
    if w_iterable is None :
        w_set.strategy = strategy = space.fromcache(EmptySetStrategy)
        w_set.sstorage = strategy.get_empty_storage()
        return

    if isinstance(w_iterable, W_BaseSetObject):
        w_set.strategy = w_iterable.strategy
        w_set.sstorage = w_iterable.get_storage_copy()
        return

    iterable_w = space.listview(w_iterable)

    if len(iterable_w) == 0:
        w_set.strategy = strategy = space.fromcache(EmptySetStrategy)
        w_set.sstorage = strategy.get_empty_storage()
        return

    # check for integers
    for w_item in iterable_w:
        if type(w_item) is not W_IntObject:
            break
    else:
        w_set.strategy = space.fromcache(IntegerSetStrategy)
        w_set.sstorage = w_set.strategy.get_storage_from_list(iterable_w)
        return

    w_set.strategy = space.fromcache(ObjectSetStrategy)
    w_set.sstorage = w_set.strategy.get_storage_from_list(iterable_w)

def _initialize_set(space, w_obj, w_iterable=None):
    w_obj.clear()
    set_strategy_and_setdata(space, w_obj, w_iterable)

def _convert_set_to_frozenset(space, w_obj):
    #XXX can be optimized
    if space.is_true(space.isinstance(w_obj, space.w_set)):
        assert isinstance(w_obj, W_SetObject)
        #XXX better instantiate?
        w_frozen = W_FrozensetObject(space, None)
        w_frozen.strategy = w_obj.strategy
        w_frozen.sstorage = w_obj.sstorage
        return w_frozen
    else:
        return None

def set_update__Set(space, w_left, others_w):
    """Update a set with the union of itself and another."""
    for w_other in others_w:
        if isinstance(w_other, W_BaseSetObject):
            w_left.update(w_other)     # optimization only
        else:
            for w_key in space.listview(w_other):
                w_left.add(w_key)

def inplace_or__Set_Set(space, w_left, w_other):
    w_left.update(w_other)
    return w_left

inplace_or__Set_Frozenset = inplace_or__Set_Set

def set_add__Set_ANY(space, w_left, w_other):
    """Add an element to a set.

    This has no effect if the element is already present.
    """
    w_left.add(w_other)

def set_copy__Set(space, w_set):
    return w_set.copy()

def frozenset_copy__Frozenset(space, w_left):
    if type(w_left) is W_FrozensetObject:
        return w_left
    else:
        return set_copy__Set(space, w_left)

def set_clear__Set(space, w_left):
    w_left.clear()

def sub__Set_Set(space, w_left, w_other):
    return w_left.difference(w_other)

sub__Set_Frozenset = sub__Set_Set
sub__Frozenset_Set = sub__Set_Set
sub__Frozenset_Frozenset = sub__Set_Set

def set_difference__Set(space, w_left, others_w):
    if len(others_w) == 0:
        return w_left.copy()
    result = w_left.copy()
    set_difference_update__Set(space, result, others_w)
    return result

frozenset_difference__Frozenset = set_difference__Set


def set_difference_update__Set(space, w_left, others_w):
    for w_other in others_w:
        if isinstance(w_other, W_BaseSetObject):
            # optimization only
            w_left.difference_update(w_other)
        else:
            w_other_as_set = w_left._newobj(space, w_other)
            w_left.difference_update(w_other_as_set)

def inplace_sub__Set_Set(space, w_left, w_other):
    w_left.difference_update(w_other)
    return w_left

inplace_sub__Set_Frozenset = inplace_sub__Set_Set

def eq__Set_Set(space, w_left, w_other):
    # optimization only (the general case is eq__Set_settypedef)
    return space.wrap(w_left.equals(w_other))

eq__Set_Frozenset = eq__Set_Set
eq__Frozenset_Frozenset = eq__Set_Set
eq__Frozenset_Set = eq__Set_Set

def eq__Set_settypedef(space, w_left, w_other):
    # tested in test_buildinshortcut.py
    #XXX do not make new setobject here
    w_other_as_set = w_left._newobj(space, w_other)
    return space.wrap(w_left.equals(w_other))

eq__Set_frozensettypedef = eq__Set_settypedef
eq__Frozenset_settypedef = eq__Set_settypedef
eq__Frozenset_frozensettypedef = eq__Set_settypedef

def eq__Set_ANY(space, w_left, w_other):
    # workaround to have "set() == 42" return False instead of falling
    # back to cmp(set(), 42) because the latter raises a TypeError
    return space.w_False

eq__Frozenset_ANY = eq__Set_ANY

def ne__Set_Set(space, w_left, w_other):
    return space.wrap(not w_left.equals(w_other))

ne__Set_Frozenset = ne__Set_Set
ne__Frozenset_Frozenset = ne__Set_Set
ne__Frozenset_Set = ne__Set_Set

def ne__Set_settypedef(space, w_left, w_other):
    #XXX this is not tested
    w_other_as_set = w_left._newobj(space, w_other)
    return space.wrap(not w_left.equals(w_other))

ne__Set_frozensettypedef = ne__Set_settypedef
ne__Frozenset_settypedef = ne__Set_settypedef
ne__Frozenset_frozensettypedef = ne__Set_settypedef


def ne__Set_ANY(space, w_left, w_other):
    # more workarounds
    return space.w_True

ne__Frozenset_ANY = ne__Set_ANY

def contains__Set_ANY(space, w_left, w_other):
    try:
        return space.newbool(w_left.has_key(w_other))
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            w_f = _convert_set_to_frozenset(space, w_other)
            if w_f is not None:
                return space.newbool(w_left.has_key(w_f))
        raise

contains__Frozenset_ANY = contains__Set_ANY

def set_issubset__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    if space.is_w(w_left, w_other):
        return space.w_True
    if w_left.length() > w_other.length():
        return space.w_False
    return space.wrap(w_left.issubset(w_other))

set_issubset__Set_Frozenset = set_issubset__Set_Set
frozenset_issubset__Frozenset_Set = set_issubset__Set_Set
frozenset_issubset__Frozenset_Frozenset = set_issubset__Set_Set

def set_issubset__Set_ANY(space, w_left, w_other):
    # not checking whether w_left is w_other here, because if that were the
    # case the more precise multimethod would have applied.

    w_other_as_set = w_left._newobj(space, w_other)

    if w_left.length() > w_other_as_set.length():
        return space.w_False
    return space.wrap(w_left.issubset(w_other_as_set))

frozenset_issubset__Frozenset_ANY = set_issubset__Set_ANY

le__Set_Set = set_issubset__Set_Set
le__Set_Frozenset = set_issubset__Set_Set
le__Frozenset_Set = set_issubset__Set_Set
le__Frozenset_Frozenset = set_issubset__Set_Set

def set_issuperset__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    if space.is_w(w_left, w_other):
        return space.w_True
    if w_left.length() < w_other.length():
        return space.w_False
    return space.wrap(w_other.issubset(w_left))

set_issuperset__Set_Frozenset = set_issuperset__Set_Set
set_issuperset__Frozenset_Set = set_issuperset__Set_Set
set_issuperset__Frozenset_Frozenset = set_issuperset__Set_Set

def set_issuperset__Set_ANY(space, w_left, w_other):
    if space.is_w(w_left, w_other):
        return space.w_True

    w_other_as_set = w_left._newobj(space, w_other)

    if w_left.length() < w_other_as_set.length():
        return space.w_False
    return space.wrap(w_other_as_set.issubset(w_left))

frozenset_issuperset__Frozenset_ANY = set_issuperset__Set_ANY

ge__Set_Set = set_issuperset__Set_Set
ge__Set_Frozenset = set_issuperset__Set_Set
ge__Frozenset_Set = set_issuperset__Set_Set
ge__Frozenset_Frozenset = set_issuperset__Set_Set

# automatic registration of "lt(x, y)" as "not ge(y, x)" would not give the
# correct answer here!
def lt__Set_Set(space, w_left, w_other):
    if w_left.length() >= w_other.length():
        return space.w_False
    else:
        return le__Set_Set(space, w_left, w_other)

lt__Set_Frozenset = lt__Set_Set
lt__Frozenset_Set = lt__Set_Set
lt__Frozenset_Frozenset = lt__Set_Set

def gt__Set_Set(space, w_left, w_other):
    if w_left.length() <= w_other.length():
        return space.w_False
    else:
        return ge__Set_Set(space, w_left, w_other)

gt__Set_Frozenset = gt__Set_Set
gt__Frozenset_Set = gt__Set_Set
gt__Frozenset_Frozenset = gt__Set_Set

def _discard_from_set(space, w_left, w_item):
    """
    Discard an element from a set, with automatic conversion to
    frozenset if the argument is a set.
    Returns True if successfully removed.
    """
    try:
        deleted = w_left.remove(w_item)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        else:
            w_f = _convert_set_to_frozenset(space, w_item)
            if w_f is None:
                raise
            deleted = w_left.remove(w_f)

    if w_left.length() == 0:
        w_left.switch_to_empty_strategy()
    return deleted

def set_discard__Set_ANY(space, w_left, w_item):
    _discard_from_set(space, w_left, w_item)

def set_remove__Set_ANY(space, w_left, w_item):
    if not _discard_from_set(space, w_left, w_item):
        space.raise_key_error(w_item)

def hash__Frozenset(space, w_set):
    multi = r_uint(1822399083) + r_uint(1822399083) + 1
    if w_set.hash != 0:
        return space.wrap(w_set.hash)
    hash = 1927868237
    hash *= (w_set.length() + 1)
    w_iterator = w_set.iter()
    while True:
        w_item = w_iterator.next_entry()
        if w_item is None:
            break
        h = space.hash_w(w_item)
        value = ((h ^ (h << 16) ^ 89869747)  * multi)
        hash = intmask(hash ^ value)
    hash = hash * 69069 + 907133923
    if hash == 0:
        hash = 590923713
    hash = intmask(hash)
    w_set.hash = hash

    return space.wrap(hash)

def set_pop__Set(space, w_left):
    return w_left.popitem()

def and__Set_Set(space, w_left, w_other):
    new_set = w_left.intersect(w_other)
    return new_set

and__Set_Frozenset = and__Set_Set
and__Frozenset_Set = and__Set_Set
and__Frozenset_Frozenset = and__Set_Set

def _intersection_multiple(space, w_left, others_w):
    return w_left.intersect_multiple(others_w)

def set_intersection__Set(space, w_left, others_w):
    if len(others_w) == 0:
        return w_left.copy()
    else:
        return _intersection_multiple(space, w_left, others_w)

frozenset_intersection__Frozenset = set_intersection__Set

def set_intersection_update__Set(space, w_left, others_w):
    w_left.intersect_multiple_update(others_w)
    return

def inplace_and__Set_Set(space, w_left, w_other):
    return w_left.intersect_update(w_other)

inplace_and__Set_Frozenset = inplace_and__Set_Set

def set_isdisjoint__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    return space.newbool(w_left.isdisjoint(w_other))

set_isdisjoint__Set_Frozenset = set_isdisjoint__Set_Set
set_isdisjoint__Frozenset_Frozenset = set_isdisjoint__Set_Set
set_isdisjoint__Frozenset_Set = set_isdisjoint__Set_Set

def set_isdisjoint__Set_ANY(space, w_left, w_other):
    #XXX may be optimized when other strategies are added
    for w_key in space.listview(w_other):
        if w_left.has_key(w_key):
            return space.w_False
    return space.w_True

frozenset_isdisjoint__Frozenset_ANY = set_isdisjoint__Set_ANY

def set_symmetric_difference__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    w_result = w_left.symmetric_difference(w_other)
    return w_result

set_symmetric_difference__Set_Frozenset = set_symmetric_difference__Set_Set
set_symmetric_difference__Frozenset_Set = set_symmetric_difference__Set_Set
set_symmetric_difference__Frozenset_Frozenset = \
                                        set_symmetric_difference__Set_Set

xor__Set_Set = set_symmetric_difference__Set_Set
xor__Set_Frozenset = set_symmetric_difference__Set_Set
xor__Frozenset_Set = set_symmetric_difference__Set_Set
xor__Frozenset_Frozenset = set_symmetric_difference__Set_Set


def set_symmetric_difference__Set_ANY(space, w_left, w_other):
    w_other_as_set = w_left._newobj(space, w_other)
    w_result = w_left.symmetric_difference(w_other_as_set)
    return w_result

frozenset_symmetric_difference__Frozenset_ANY = \
        set_symmetric_difference__Set_ANY

def set_symmetric_difference_update__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    w_left.symmetric_difference_update(w_other)

set_symmetric_difference_update__Set_Frozenset = \
                                    set_symmetric_difference_update__Set_Set

def set_symmetric_difference_update__Set_ANY(space, w_left, w_other):
    w_other_as_set = w_left._newobj(space, w_other)
    w_left.symmetric_difference_update(w_other_as_set)

def inplace_xor__Set_Set(space, w_left, w_other):
    set_symmetric_difference_update__Set_Set(space, w_left, w_other)
    return w_left

inplace_xor__Set_Frozenset = inplace_xor__Set_Set

def or__Set_Set(space, w_left, w_other):
    w_copy = w_left.copy()
    w_copy.update(w_other)
    return w_copy

or__Set_Frozenset = or__Set_Set
or__Frozenset_Set = or__Set_Set
or__Frozenset_Frozenset = or__Set_Set

def set_union__Set(space, w_left, others_w):
    result = w_left.copy()
    for w_other in others_w:
        if isinstance(w_other, W_BaseSetObject):
            result.update(w_other)     # optimization only
        else:
            for w_key in space.listview(w_other):
                result.add(w_key)
    return result

frozenset_union__Frozenset = set_union__Set

def len__Set(space, w_left):
    return space.newint(w_left.length())

len__Frozenset = len__Set

def iter__Set(space, w_left):
    return W_SetIterObject(space, w_left.iter())

iter__Frozenset = iter__Set

def cmp__Set_settypedef(space, w_left, w_other):
    # hack hack until we get the expected result
    raise OperationError(space.w_TypeError,
            space.wrap('cannot compare sets using cmp()'))

cmp__Set_frozensettypedef = cmp__Set_settypedef
cmp__Frozenset_settypedef = cmp__Set_settypedef
cmp__Frozenset_frozensettypedef = cmp__Set_settypedef

init_signature = Signature(['some_iterable'], None, None)
init_defaults = [None]
def init__Set(space, w_set, __args__):
    w_iterable, = __args__.parse_obj(
            None, 'set',
            init_signature,
            init_defaults)
    _initialize_set(space, w_set, w_iterable)

app = gateway.applevel("""
    def setrepr(currently_in_repr, s):
        'The app-level part of repr().'
        set_id = id(s)
        if set_id in currently_in_repr:
            return '%s(...)' % (s.__class__.__name__,)
        currently_in_repr[set_id] = 1
        try:
            return '%s(%s)' % (s.__class__.__name__, [x for x in s])
        finally:
            try:
                del currently_in_repr[set_id]
            except:
                pass
""", filename=__file__)

setrepr = app.interphook("setrepr")

def repr__Set(space, w_set):
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return setrepr(space, w_currently_in_repr, w_set)

repr__Frozenset = repr__Set

app = gateway.applevel("""
    def reduce__Set(s):
        dict = getattr(s,'__dict__', None)
        return (s.__class__, (tuple(s),), dict)

""", filename=__file__)

set_reduce__Set = app.interphook('reduce__Set')
frozenset_reduce__Frozenset = app.interphook('reduce__Set')

from pypy.objspace.std import frozensettype
from pypy.objspace.std import settype

register_all(vars(), settype, frozensettype)
