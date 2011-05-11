from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.rlib.objectmodel import r_dict
from pypy.rlib.rarithmetic import intmask, r_uint
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.interpreter.argument import Signature
from pypy.interpreter.function import Defaults
from pypy.objspace.std.settype import set_typedef as settypedef
from pypy.objspace.std.frozensettype import frozenset_typedef as frozensettypedef
from pypy.rlib import rerased
from pypy.rlib.objectmodel import instantiate
from pypy.interpreter.generator import GeneratorIterator
from pypy.objspace.std.listobject import W_ListObject

def get_strategy_from_w_iterable(space, w_iterable=None):
    from pypy.objspace.std.intobject import W_IntObject
    #XXX what types for w_iterable are possible

    if isinstance(w_iterable, W_BaseSetObject):
        return w_iterable.strategy

    if w_iterable is None:
        #XXX becomes EmptySetStrategy later
        return space.fromcache(ObjectSetStrategy)

    if not isinstance(w_iterable, list):
        w_iterable = space.listview(w_iterable)
    for item_w in w_iterable:
        if type(item_w) is not W_IntObject:
            break;
        if item_w is w_iterable[-1]:
            return space.fromcache(IntegerSetStrategy)

    return space.fromcache(ObjectSetStrategy)

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

    def __init__(w_self, space, setdata):
        """Initialize the set by taking ownership of 'setdata'."""
        assert setdata is not None
        w_self.space = space #XXX less memory without this indirection?
        w_self.strategy = get_strategy_from_w_iterable(space, setdata.keys())
        w_self.strategy.init_from_setdata_w(w_self, setdata)

    def __repr__(w_self):
        """representation for debugging purposes"""
        reprlist = [repr(w_item) for w_item in w_self.getkeys()]
        return "<%s(%s)>" % (w_self.__class__.__name__, ', '.join(reprlist))

    def _newobj(w_self, space, rdict_w=None):
        """Make a new set or frozenset by taking ownership of 'rdict_w'."""
        #return space.call(space.type(w_self),W_SetIterObject(rdict_w))
        objtype = type(w_self)
        if objtype is W_SetObject:
            obj = W_SetObject(space, rdict_w)
        elif objtype is W_FrozensetObject:
            obj = W_FrozensetObject(space, rdict_w)
        else:
            itemiterator = space.iter(W_SetIterObject(rdict_w))
            obj = space.call_function(space.type(w_self),itemiterator)
        return obj

    _lifeline_ = None
    def getweakref(self):
        return self._lifeline_

    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline

    def switch_to_object_strategy(self, space):
        d = self.strategy.getdict_w(self)
        self.strategy = space.fromcache(ObjectSetStrategy)
        self.sstorage = self.strategy.cast_to_void_star(d)

    # _____________ strategy methods ________________

    def clear(self):
        self.strategy.clear(self)

    def copy(self):
        return self.strategy.copy(self)

    def length(self):
        return self.strategy.length(self)

    def add(self, w_key):
        self.strategy.add(self, w_key)

    def discard(self, w_item):
        return self.strategy.discard(self, w_item)

    def delitem(self, w_item):
        return self.strategy.delitem(self, w_item)

    def getdict_w(self):
        return self.strategy.getdict_w(self)

    def getkeys(self):
        return self.strategy.getkeys(self)

    def difference(self, w_other):
        return self.strategy.difference(self, w_other)

    def difference_update(self, w_other):
        return self.strategy.difference_update(self, w_other)

    def symmetric_difference(self, w_other):
        return self.strategy.symmetric_difference(self, w_other)

    def symmetric_difference_update(self, w_other):
        return self.strategy.symmetric_difference_update(self, w_other)

    def intersect(self, w_other):
        return self.strategy.intersect(self, w_other)

    def intersect_update(self, w_other):
        return self.strategy.intersect_update(self, w_other)

    def intersect_multiple(self, others_w):
        return self.strategy.intersect_multiple(self, others_w)

    def intersect_multiple_update(self, others_w):
        self.strategy.intersect_multiple_update(self, others_w)

    def issubset(self, w_other):
        return self.strategy.issubset(self, w_other)

    def isdisjoint(self, w_other):
        return self.strategy.isdisjoint(self, w_other)

    def update(self, w_other):
        self.strategy.update(self, w_other)

    def has_key(self, w_key):
        return self.strategy.has_key(self, w_key)

    def equals(self, w_other):
        return self.strategy.equals(self, w_other)

class W_SetObject(W_BaseSetObject):
    from pypy.objspace.std.settype import set_typedef as typedef

class W_FrozensetObject(W_BaseSetObject):
    from pypy.objspace.std.frozensettype import frozenset_typedef as typedef
    hash = 0

registerimplementation(W_BaseSetObject)
registerimplementation(W_SetObject)
registerimplementation(W_FrozensetObject)

class SetStrategy(object):
    def __init__(self, space):
        self.space = space

    def init_from_w_iterable(self, w_set, setdata):
        raise NotImplementedError

    def length(self, w_set):
        raise NotImplementedError

class AbstractUnwrappedSetStrategy(object):
    __mixin__ = True

    def get_empty_storage(self):
        raise NotImplementedError

    def init_from_w_iterable(self, w_set, w_iterable):
        setdata = self.make_setdata_from_w_iterable(w_iterable)
        w_set.sstorage = self.cast_to_void_star(setdata)

    def init_from_setdata_w(self, w_set, setdata_w):
        d = self.get_empty_dict()
        for item_w in setdata_w.keys():
            d[self.unwrap(item_w)] = None
        w_set.sstorage = self.cast_to_void_star(d)

    def make_setdata_from_w_iterable(self, w_iterable):
        """Return a new r_dict with the content of w_iterable."""
        if isinstance(w_iterable, W_BaseSetObject):
            return self.cast_from_void_star(w_set.sstorage).copy()
        data = self.get_empty_dict()
        if w_iterable is not None:
            for w_item in self.space.listview(w_iterable):
                data[self.unwrap(w_item)] = None
        return data

    def length(self, w_set):
        return len(self.cast_from_void_star(w_set.sstorage))

    def clear(self, w_set):
        self.cast_from_void_star(w_set.sstorage).clear()

    def copy(self, w_set):
        #XXX do not copy FrozenDict
        d = self.cast_from_void_star(w_set.sstorage)
        #XXX make it faster by using from_storage_and_strategy
        clone = w_set._newobj(self.space, newset(self.space))
        clone.strategy = w_set.strategy
        clone.sstorage = self.cast_to_void_star(d.copy())
        return clone

    def add(self, w_set, w_key):
        if self.is_correct_type(w_key):
            d = self.cast_from_void_star(w_set.sstorage)
            d[self.unwrap(w_key)] = None
        else:
            w_set.switch_to_object_strategy(self.space)
            w_set.add(w_key)

    def delitem(self, w_set, w_item):
        # not a normal set operation; only used internally
        d = self.cast_from_void_star(w_set.sstorage)
        try:
            del d[self.unwrap(w_item)]
        except KeyError:
            raise

    def discard(self, w_set, w_item):
        d = self.cast_from_void_star(w_set.sstorage)
        try:
            del d[self.unwrap(w_item)]
            return True
        except KeyError:
            return False
        except OperationError, e:
            if not e.match(self.space, self.space.w_TypeError):
                raise
            w_f = _convert_set_to_frozenset(self.space, w_item)
            if w_f is None:
                raise
        try:
            del d[w_f]
            return True
        except KeyError:
            return False
        except OperationError, e:
            #XXX is this ever tested?
            assert False
            if not e.match(space, space.w_TypeError):
                raise
            return False

    def getdict_w(self, w_set):
        result = newset(self.space)
        keys = self.cast_from_void_star(w_set.sstorage).keys()
        for key in keys:
            result[self.wrap(key)] = None
        return result

    def getkeys(self, w_set):
        keys = self.cast_from_void_star(w_set.sstorage).keys()
        keys_w = [self.wrap(key) for key in keys]
        return keys_w

    def has_key(self, w_set, w_key):
        dict_w = self.cast_from_void_star(w_set.sstorage)
        return self.unwrap(w_key) in dict_w

    def equals(self, w_set, w_other):
        if w_set.length() != w_other.length():
            return False
        items = self.cast_from_void_star(w_set.sstorage).keys()
        for key in items:
            if not w_other.has_key(self.wrap(key)):
                return False
        return True

    def difference(self, w_set, w_other):
        result = w_set._newobj(self.space, newset(self.space))
        if not isinstance(w_other, W_BaseSetObject):
            #XXX this is bad
            setdata = make_setdata_from_w_iterable(self.space, w_other)
            w_other = w_set._newobj(self.space, setdata)
        for w_key in w_set.getkeys():
            if not w_other.has_key(w_key):
                result.add(w_key)
        return result

    def difference_update(self, w_set, w_other):
        if w_set is w_other:
            w_set.clear()     # for the case 'a.difference_update(a)'
        else:
            for w_key in w_other.getkeys():
                try:
                    self.delitem(w_set, w_key)
                except KeyError:
                    pass

    def symmetric_difference(self, w_set, w_other):
        #XXX no wrapping when strategies are equal
        result = w_set._newobj(self.space, newset(self.space))
        for w_key in w_set.getkeys():
            if not w_other.has_key(w_key):
                result.add(w_key)
        for w_key in w_other.getkeys():
            if not w_set.has_key(w_key):
                result.add(w_key)
        return result

    def symmetric_difference_update(self, w_set, w_other):
        #XXX no wrapping when strategies are equal
        newsetdata = newset(self.space)
        for w_key in w_set.getkeys():
            if not w_other.has_key(w_key):
                newsetdata[w_key] = None
        for w_key in w_other.getkeys():
            if not w_set.has_key(w_key):
                newsetdata[w_key] = None

        # do not switch strategy here if other items match
        w_set.strategy = strategy = self.space.fromcache(ObjectSetStrategy)
        w_set.sstorage = strategy.cast_to_void_star(newsetdata)

    def intersect(self, w_set, w_other):
        if w_set.length() > w_other.length():
            return w_other.intersect(w_set)

        result = w_set._newobj(self.space, newset(self.space))
        items = self.cast_from_void_star(w_set.sstorage).keys()
        #XXX do it without wrapping when strategies are equal
        for key in items:
            w_key = self.wrap(key)
            if w_other.has_key(w_key):
                result.add(w_key)
        return result

    def intersect_update(self, w_set, w_other):
        if w_set.length() > w_other.length():
            return w_other.intersect(w_set)

        setdata = newset(self.space)
        items = self.cast_from_void_star(w_set.sstorage).keys()
        for key in items:
            w_key = self.wrap(key)
            if w_other.has_key(w_key):
                setdata[w_key] = None

        # do not switch strategy here if other items match
        w_set.strategy = strategy = self.space.fromcache(ObjectSetStrategy)
        w_set.sstorage = strategy.cast_to_void_star(setdata)
        return w_set

    def intersect_multiple(self, w_set, others_w):
        result = w_set
        for w_other in others_w:
            if isinstance(w_other, W_BaseSetObject):
                # optimization only
                #XXX this creates setobject again
                result = result.intersect(w_other)
            else:
                #XXX directly give w_other as argument to result2
                result2 = w_set._newobj(self.space, newset(self.space))
                for w_key in self.space.listview(w_other):
                    if result.has_key(w_key):
                        result2.add(w_key)
                result = result2
        return result

    def intersect_multiple_update(self, w_set, others_w):
        #XXX faster withouth creating the setobject in intersect_multiple
        result = self.intersect_multiple(w_set, others_w)
        w_set.strategy = result.strategy
        w_set.sstorage = result.sstorage

    def issubset(self, w_set, w_other):
        if not isinstance(w_other, W_BaseSetObject):
            setdata = make_setdata_from_w_iterable(self.space, w_other)
            w_other = w_set._newobj(self.space, setdata)

        if w_set.length() > w_other.length():
            return False

        #XXX add ways without unwrapping if strategies are equal
        for w_key in w_set.getkeys():
            if not w_other.has_key(w_key):
                return False
        return True

    def isdisjoint(self, w_set, w_other):
        if w_set.length() > w_other.length():
            return w_other.isdisjoint(w_set)

        d = self.cast_from_void_star(w_set.sstorage)
        for key in d:
            #XXX no need to wrap, if strategies are equal
            if w_other.has_key(self.wrap(key)):
                return False
        return True

    def update(self, w_set, w_other):
        d = self.cast_from_void_star(w_set.sstorage)
        if w_set.strategy is self.space.fromcache(ObjectSetStrategy):
            other_w = w_other.getkeys()
            #XXX better solution!?
            for w_key in other_w:
                d[w_key] = None
            return

        elif w_set.strategy is w_other.strategy:
            other = self.cast_from_void_star(w_other.sstorage)
            d.update(other)
            return
        w_set.switch_to_object_strategy(self.space)
        w_set.update(w_other)

class IntegerSetStrategy(AbstractUnwrappedSetStrategy, SetStrategy):
    cast_to_void_star, cast_from_void_star = rerased.new_erasing_pair("integer")
    cast_to_void_star = staticmethod(cast_to_void_star)
    cast_from_void_star = staticmethod(cast_from_void_star)

    def get_empty_dict(self):
        return {}

    def is_correct_type(self, w_key):
        from pypy.objspace.std.intobject import W_IntObject
        return type(w_key) is W_IntObject

    def unwrap(self, w_item):
        return self.space.unwrap(w_item)

    def wrap(self, item):
        return self.space.wrap(item)

class ObjectSetStrategy(AbstractUnwrappedSetStrategy, SetStrategy):
    cast_to_void_star, cast_from_void_star = rerased.new_erasing_pair("object")
    cast_to_void_star = staticmethod(cast_to_void_star)
    cast_from_void_star = staticmethod(cast_from_void_star)

    def get_empty_dict(self):
        return newset(self.space)

    def is_correct_type(self, w_key):
        return True

    def unwrap(self, w_item):
        return w_item

    def wrap(self, item):
        return item

class W_SetIterObject(W_Object):
    from pypy.objspace.std.settype import setiter_typedef as typedef

    def __init__(w_self, setdata):
        w_self.content = content = setdata
        w_self.len = len(content)
        w_self.pos = 0
        w_self.iterator = iter(w_self.content)

    def next_entry(w_self):
        for w_key in w_self.iterator:
            return w_key
        else:
            return None

registerimplementation(W_SetIterObject)

def iter__SetIterObject(space, w_setiter):
    return w_setiter

def next__SetIterObject(space, w_setiter):
    content = w_setiter.content
    if content is not None:
        if w_setiter.len != len(content):
            w_setiter.len = -1   # Make this error state sticky
            raise OperationError(space.w_RuntimeError,
                     space.wrap("Set changed size during iteration"))
        # look for the next entry
        w_result = w_setiter.next_entry()
        if w_result is not None:
            w_setiter.pos += 1
            return w_result
        # no more entries
        w_setiter.content = None
    raise OperationError(space.w_StopIteration, space.w_None)

# XXX __length_hint__()
##def len__SetIterObject(space, w_setiter):
##    content = w_setiter.content
##    if content is None or w_setiter.len == -1:
##        return space.wrap(0)
##    return space.wrap(w_setiter.len - w_setiter.pos)

# some helper functions

def newset(space):
    return r_dict(space.eq_w, space.hash_w)

def make_setdata_from_w_iterable(space, w_iterable=None):
    #XXX remove this later
    """Return a new r_dict with the content of w_iterable."""
    if isinstance(w_iterable, W_BaseSetObject):
        #XXX is this bad or not?
        return w_iterable.getdict_w()
    data = newset(space)
    if w_iterable is not None:
        for w_item in space.listview(w_iterable):
            data[w_item] = None
    return data

def _initialize_set(space, w_obj, w_iterable=None):
    w_obj.clear()
    if w_iterable is not None:
        if  isinstance(w_iterable, GeneratorIterator):
            w_iterable = W_ListObject(space.listview(w_iterable))
        w_obj.strategy = get_strategy_from_w_iterable(space, w_iterable)
        w_obj.strategy.init_from_w_iterable(w_obj, w_iterable)

def _convert_set_to_frozenset(space, w_obj):
    #XXX can be optimized
    if space.is_true(space.isinstance(w_obj, space.w_set)):
        w_frozen = instantiate(W_FrozensetObject)
        w_frozen.strategy = w_obj.strategy
        w_frozen.sstorage = w_obj.sstorage
        return w_frozen
    else:
        return None

# helper functions for set operation on dicts

def _symmetric_difference_dict(space, ld, rd):
    result = newset(space)
    for w_key in ld:
        if w_key not in rd:
            result[w_key] = None
    for w_key in rd:
        if w_key not in ld:
            result[w_key] = None
    return result

def _issubset_dict(ldict, rdict):
    if len(ldict) > len(rdict):
        return False

    for w_key in ldict:
        if w_key not in rdict:
            return False
    return True


#end helper functions

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
    result = w_left
    for w_other in others_w:
        result = result.difference(w_other)
    return result

frozenset_difference__Frozenset = set_difference__Set


def set_difference_update__Set(space, w_left, others_w):
    for w_other in others_w:
        if isinstance(w_other, W_BaseSetObject):
            # optimization only
            w_left.difference_update(w_other)
        else:
            for w_key in space.listview(w_other):
                try:
                    w_left.delitem(w_key)
                except KeyError:
                    pass

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
    setdata = make_setdata_from_w_iterable(space, w_other)
    w_other_as_set = w_left._newobj(space, setdata)
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
    rd = make_setdata_from_w_iterable(space, w_other)
    return space.wrap(_is_eq(w_left.setdata, rd))

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
    return space.wrap(w_left.issubset(w_other))

set_issubset__Set_Frozenset = set_issubset__Set_Set
frozenset_issubset__Frozenset_Set = set_issubset__Set_Set
frozenset_issubset__Frozenset_Frozenset = set_issubset__Set_Set

def set_issubset__Set_ANY(space, w_left, w_other):
    if space.is_w(w_left, w_other):
        return space.w_True

    return space.wrap(w_left.issubset(w_other))

frozenset_issubset__Frozenset_ANY = set_issubset__Set_ANY

le__Set_Set = set_issubset__Set_Set
le__Set_Frozenset = set_issubset__Set_Set
le__Frozenset_Set = set_issubset__Set_Set
le__Frozenset_Frozenset = set_issubset__Set_Set

def set_issuperset__Set_Set(space, w_left, w_other):
    # optimization only (the general case works too)
    #XXX this is the same code as in set_issubset__Set_Set (sets reversed)
    if space.is_w(w_left, w_other):
        return space.w_True

    return space.wrap(w_other.issubset(w_left))

set_issuperset__Set_Frozenset = set_issuperset__Set_Set
set_issuperset__Frozenset_Set = set_issuperset__Set_Set
set_issuperset__Frozenset_Frozenset = set_issuperset__Set_Set

def set_issuperset__Set_ANY(space, w_left, w_other):
    if space.is_w(w_left, w_other):
        return space.w_True

    #XXX BAD
    setdata = make_setdata_from_w_iterable(space, w_other)
    w_other = w_left._newobj(space, setdata)

    return space.wrap(w_other.issubset(w_left))

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
    x = w_left.discard(w_item)
    return x

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
    for w_item in w_set.getkeys():
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
    #XXX move this to strategy so we don't have to
    #    wrap all items only to get the first one
    for w_key in w_left.getkeys():
        break
    else:
        raise OperationError(space.w_KeyError,
                                space.wrap('pop from an empty set'))
    w_left.delitem(w_key)
    return w_key

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
    #XXX maybe checking if type fits strategy first (before comparing) speeds this up a bit
    #    since this will be used in many other functions -> general function for that
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
    #XXX deal with iterables withouth turning them into sets
    setdata = make_setdata_from_w_iterable(space, w_other)
    w_other_as_set = w_left._newobj(space, setdata)

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
    #XXX deal with iterables withouth turning them into sets
    setdata = make_setdata_from_w_iterable(space, w_other)
    w_other_as_set = w_left._newobj(space, setdata)
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
    return W_SetIterObject(w_left.getkeys())

iter__Frozenset = iter__Set

def cmp__Set_settypedef(space, w_left, w_other):
    # hack hack until we get the expected result
    raise OperationError(space.w_TypeError,
            space.wrap('cannot compare sets using cmp()'))

cmp__Set_frozensettypedef = cmp__Set_settypedef
cmp__Frozenset_settypedef = cmp__Set_settypedef
cmp__Frozenset_frozensettypedef = cmp__Set_settypedef

init_signature = Signature(['some_iterable'], None, None)
init_defaults = Defaults([None])
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
