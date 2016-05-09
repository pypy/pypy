import weakref, sys

from rpython.rlib import jit, objectmodel, debug, rerased
from rpython.rlib.rarithmetic import intmask, r_uint

from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.dictmultiobject import (
    W_DictMultiObject, DictStrategy, ObjectDictStrategy, BaseKeyIterator,
    BaseValueIterator, BaseItemIterator, _never_equal_to_string,
    W_DictObject,
)
from pypy.objspace.std.typeobject import MutableCell


erase_item, unerase_item = rerased.new_erasing_pair("mapdict storage item")
erase_map,  unerase_map = rerased.new_erasing_pair("map")
erase_list, unerase_list = rerased.new_erasing_pair("mapdict storage list")


# ____________________________________________________________
# attribute shapes

NUM_DIGITS = 4
NUM_DIGITS_POW2 = 1 << NUM_DIGITS
# note: we use "x * NUM_DIGITS_POW2" instead of "x << NUM_DIGITS" because
# we want to propagate knowledge that the result cannot be negative


class AbstractAttribute(object):
    _immutable_fields_ = ['terminator']
    cache_attrs = None
    _size_estimate = 0

    def __init__(self, space, terminator):
        self.space = space
        assert isinstance(terminator, Terminator)
        self.terminator = terminator

    def read(self, obj, name, index):
        attr = self.find_map_attr(name, index)
        if attr is None:
            return self.terminator._read_terminator(obj, name, index)
        if (
            jit.isconstant(attr.storageindex) and
            jit.isconstant(obj) and
            not attr.ever_mutated
        ):
            return self._pure_mapdict_read_storage(obj, attr.storageindex)
        else:
            return obj._mapdict_read_storage(attr.storageindex)

    @jit.elidable
    def _pure_mapdict_read_storage(self, obj, storageindex):
        return obj._mapdict_read_storage(storageindex)

    def write(self, obj, name, index, w_value):
        attr = self.find_map_attr(name, index)
        if attr is None:
            return self.terminator._write_terminator(obj, name, index, w_value)
        if not attr.ever_mutated:
            attr.ever_mutated = True
        obj._mapdict_write_storage(attr.storageindex, w_value)
        return True

    def delete(self, obj, name, index):
        pass

    @jit.elidable
    def find_map_attr(self, name, index):
        # attr cache
        space = self.space
        cache = space.fromcache(MapAttrCache)
        SHIFT2 = r_uint.BITS - space.config.objspace.std.methodcachesizeexp
        SHIFT1 = SHIFT2 - 5
        attrs_as_int = objectmodel.current_object_addr_as_int(self)
        # ^^^Note: see comment in typeobject.py for
        # _pure_lookup_where_with_method_cache()

        # unrolled hash computation for 2-tuple
        c1 = 0x345678
        c2 = 1000003
        hash_name = objectmodel.compute_hash(name)
        hash_selector = intmask((c2 * ((c2 * c1) ^ hash_name)) ^ index)
        product = intmask(attrs_as_int * hash_selector)
        attr_hash = (r_uint(product) ^ (r_uint(product) << SHIFT1)) >> SHIFT2
        # ^^^Note2: same comment too
        cached_attr = cache.attrs[attr_hash]
        if cached_attr is self:
            cached_name = cache.names[attr_hash]
            cached_index = cache.indexes[attr_hash]
            if cached_name == name and cached_index == index:
                attr = cache.cached_attrs[attr_hash]
                if space.config.objspace.std.withmethodcachecounter:
                    cache.hits[name] = cache.hits.get(name, 0) + 1
                return attr
        attr = self._find_map_attr(name, index)
        cache.attrs[attr_hash] = self
        cache.names[attr_hash] = name
        cache.indexes[attr_hash] = index
        cache.cached_attrs[attr_hash] = attr
        if space.config.objspace.std.withmethodcachecounter:
            cache.misses[name] = cache.misses.get(name, 0) + 1
        return attr

    def _find_map_attr(self, name, index):
        while isinstance(self, PlainAttribute):
            if index == self.index and name == self.name:
                return self
            self = self.back
        return None

    def copy(self, obj):
        raise NotImplementedError("abstract base class")

    def length(self):
        raise NotImplementedError("abstract base class")

    def get_terminator(self):
        return self.terminator

    def set_terminator(self, obj, terminator):
        raise NotImplementedError("abstract base class")

    @jit.elidable
    def size_estimate(self):
        return self._size_estimate >> NUM_DIGITS

    def search(self, attrtype):
        return None

    @jit.elidable
    def _get_new_attr(self, name, index):
        cache = self.cache_attrs
        if cache is None:
            cache = self.cache_attrs = {}
        attr = cache.get((name, index), None)
        if attr is None:
            attr = PlainAttribute(name, index, self)
            cache[name, index] = attr
        return attr

    def add_attr(self, obj, name, index, w_value):
        self._reorder_and_add(obj, name, index, w_value)
        if not jit.we_are_jitted():
            oldattr = self
            attr = obj._get_mapdict_map()
            size_est = (oldattr._size_estimate + attr.size_estimate()
                                               - oldattr.size_estimate())
            assert size_est >= (oldattr.length() * NUM_DIGITS_POW2)
            oldattr._size_estimate = size_est

    def _add_attr_without_reordering(self, obj, name, index, w_value):
        attr = self._get_new_attr(name, index)
        attr._switch_map_and_write_storage(obj, w_value)

    @jit.unroll_safe
    def _switch_map_and_write_storage(self, obj, w_value):
        if self.length() > obj._mapdict_storage_length():
            # note that self.size_estimate() is always at least self.length()
            new_storage = [None] * self.size_estimate()
            for i in range(obj._mapdict_storage_length()):
                new_storage[i] = obj._mapdict_read_storage(i)
            obj._set_mapdict_storage_and_map(new_storage, self)

        # the order is important here: first change the map, then the storage,
        # for the benefit of the special subclasses
        obj._set_mapdict_map(self)
        obj._mapdict_write_storage(self.storageindex, w_value)


    @jit.elidable
    def _find_branch_to_move_into(self, name, index):
        # walk up the map chain to find an ancestor with lower order that
        # already has the current name as a child inserted
        current_order = sys.maxint
        number_to_readd = 0
        current = self
        key = (name, index)
        while True:
            attr = None
            if current.cache_attrs is not None:
                attr = current.cache_attrs.get(key, None)
            if attr is None or attr.order > current_order:
                # we reached the top, so we didn't find it anywhere,
                # just add it to the top attribute
                if not isinstance(current, PlainAttribute):
                    return 0, self._get_new_attr(name, index)

            else:
                return number_to_readd, attr
            # if not found try parent
            number_to_readd += 1
            current_order = current.order
            current = current.back

    @jit.look_inside_iff(lambda self, obj, name, index, w_value:
            jit.isconstant(self) and
            jit.isconstant(name) and
            jit.isconstant(index))
    def _reorder_and_add(self, obj, name, index, w_value):
        # the idea is as follows: the subtrees of any map are ordered by
        # insertion.  the invariant is that subtrees that are inserted later
        # must not contain the name of the attribute of any earlier inserted
        # attribute anywhere
        #                              m______
        #         inserted first      / \ ... \   further attributes
        #           attrname a      0/  1\    n\
        #                           m  a must not appear here anywhere
        #
        # when inserting a new attribute in an object we check whether any
        # parent of lower order has seen that attribute yet. if yes, we follow
        # that branch. if not, we normally append that attribute. When we
        # follow a prior branch, we necessarily remove some attributes to be
        # able to do that. They need to be re-added, which has to follow the
        # reordering procedure recusively.

        # we store the to-be-readded attribute in the stack, with the map and
        # the value paired up those are lazily initialized to a list large
        # enough to store all current attributes
        stack = None
        stack_index = 0
        while True:
            current = self
            number_to_readd = 0
            number_to_readd, attr = self._find_branch_to_move_into(name, index)
            # we found the attributes further up, need to save the
            # previous values of the attributes we passed
            if number_to_readd:
                if stack is None:
                    stack = [erase_map(None)] * (self.length() * 2)
                current = self
                for i in range(number_to_readd):
                    assert isinstance(current, PlainAttribute)
                    w_self_value = obj._mapdict_read_storage(
                            current.storageindex)
                    stack[stack_index] = erase_map(current)
                    stack[stack_index + 1] = erase_item(w_self_value)
                    stack_index += 2
                    current = current.back
            attr._switch_map_and_write_storage(obj, w_value)

            if not stack_index:
                return

            # readd the current top of the stack
            stack_index -= 2
            next_map = unerase_map(stack[stack_index])
            w_value = unerase_item(stack[stack_index + 1])
            name = next_map.name
            index = next_map.index
            self = obj._get_mapdict_map()

    def materialize_r_dict(self, space, obj, dict_w):
        raise NotImplementedError("abstract base class")

    def remove_dict_entries(self, obj):
        raise NotImplementedError("abstract base class")

    def __repr__(self):
        return "<%s>" % (self.__class__.__name__,)


class Terminator(AbstractAttribute):
    _immutable_fields_ = ['w_cls']

    def __init__(self, space, w_cls):
        AbstractAttribute.__init__(self, space, self)
        self.w_cls = w_cls

    def _read_terminator(self, obj, name, index):
        return None

    def _write_terminator(self, obj, name, index, w_value):
        obj._get_mapdict_map().add_attr(obj, name, index, w_value)
        return True

    def copy(self, obj):
        result = Object()
        result.space = self.space
        result._mapdict_init_empty(self)
        return result

    def length(self):
        return 0

    def set_terminator(self, obj, terminator):
        result = Object()
        result.space = self.space
        result._mapdict_init_empty(terminator)
        return result

    def remove_dict_entries(self, obj):
        return self.copy(obj)

    def __repr__(self):
        return "<%s w_cls=%s>" % (self.__class__.__name__, self.w_cls)

class DictTerminator(Terminator):
    _immutable_fields_ = ['devolved_dict_terminator']
    def __init__(self, space, w_cls):
        Terminator.__init__(self, space, w_cls)
        self.devolved_dict_terminator = DevolvedDictTerminator(space, w_cls)

    def materialize_r_dict(self, space, obj, dict_w):
        result = Object()
        result.space = space
        result._mapdict_init_empty(self.devolved_dict_terminator)
        return result


class NoDictTerminator(Terminator):
    def _write_terminator(self, obj, name, index, w_value):
        if index == DICT:
            return False
        return Terminator._write_terminator(self, obj, name, index, w_value)


class DevolvedDictTerminator(Terminator):
    def _read_terminator(self, obj, name, index):
        if index == DICT:
            space = self.space
            w_dict = obj.getdict(space)
            return space.finditem_str(w_dict, name)
        return Terminator._read_terminator(self, obj, name, index)

    def _write_terminator(self, obj, name, index, w_value):
        if index == DICT:
            space = self.space
            w_dict = obj.getdict(space)
            space.setitem_str(w_dict, name, w_value)
            return True
        return Terminator._write_terminator(self, obj, name, index, w_value)

    def delete(self, obj, name, index):
        from pypy.interpreter.error import OperationError
        if index == DICT:
            space = self.space
            w_dict = obj.getdict(space)
            try:
                space.delitem(w_dict, space.wrap(name))
            except OperationError as ex:
                if not ex.match(space, space.w_KeyError):
                    raise
            return Terminator.copy(self, obj)
        return Terminator.delete(self, obj, name, index)

    def remove_dict_entries(self, obj):
        assert 0, "should be unreachable"

    def set_terminator(self, obj, terminator):
        if not isinstance(terminator, DevolvedDictTerminator):
            assert isinstance(terminator, DictTerminator)
            terminator = terminator.devolved_dict_terminator
        return Terminator.set_terminator(self, obj, terminator)

class PlainAttribute(AbstractAttribute):
    _immutable_fields_ = ['name', 'index', 'storageindex', 'back', 'ever_mutated?', 'order']

    def __init__(self, name, index, back):
        AbstractAttribute.__init__(self, back.space, back.terminator)
        self.name = name
        self.index = index
        self.storageindex = back.length()
        self.back = back
        self._size_estimate = self.length() * NUM_DIGITS_POW2
        self.ever_mutated = False
        self.order = len(back.cache_attrs) if back.cache_attrs else 0

    def _copy_attr(self, obj, new_obj):
        w_value = self.read(obj, self.name, self.index)
        new_obj._get_mapdict_map().add_attr(new_obj, self.name, self.index, w_value)

    def delete(self, obj, name, index):
        if index == self.index and name == self.name:
            # ok, attribute is deleted
            if not self.ever_mutated:
                self.ever_mutated = True
            return self.back.copy(obj)
        new_obj = self.back.delete(obj, name, index)
        if new_obj is not None:
            self._copy_attr(obj, new_obj)
        return new_obj

    def copy(self, obj):
        new_obj = self.back.copy(obj)
        self._copy_attr(obj, new_obj)
        return new_obj

    def length(self):
        return self.storageindex + 1

    def set_terminator(self, obj, terminator):
        new_obj = self.back.set_terminator(obj, terminator)
        self._copy_attr(obj, new_obj)
        return new_obj

    def search(self, attrtype):
        if self.index == attrtype:
            return self
        return self.back.search(attrtype)

    def materialize_r_dict(self, space, obj, dict_w):
        new_obj = self.back.materialize_r_dict(space, obj, dict_w)
        if self.index == DICT:
            w_attr = space.wrap(self.name)
            dict_w[w_attr] = obj._mapdict_read_storage(self.storageindex)
        else:
            self._copy_attr(obj, new_obj)
        return new_obj

    def remove_dict_entries(self, obj):
        new_obj = self.back.remove_dict_entries(obj)
        if self.index != DICT:
            self._copy_attr(obj, new_obj)
        return new_obj

    def __repr__(self):
        return "<PlainAttribute %s %s %s %r>" % (self.name, self.index, self.storageindex, self.back)

class MapAttrCache(object):
    def __init__(self, space):
        SIZE = 1 << space.config.objspace.std.methodcachesizeexp
        self.attrs = [None] * SIZE
        self.names = [None] * SIZE
        self.indexes = [INVALID] * SIZE
        self.cached_attrs = [None] * SIZE
        if space.config.objspace.std.withmethodcachecounter:
            self.hits = {}
            self.misses = {}

    def clear(self):
        for i in range(len(self.attrs)):
            self.attrs[i] = None
        for i in range(len(self.names)):
            self.names[i] = None
            self.indexes[i] = INVALID
        for i in range(len(self.cached_attrs)):
            self.cached_attrs[i] = None

# ____________________________________________________________
# object implementation

DICT = 0
SPECIAL = 1
INVALID = 2
SLOTS_STARTING_FROM = 3

# a little bit of a mess of mixin classes that implement various pieces of
# objspace user object functionality in terms of mapdict

class BaseUserClassMapdict:
    # everything that's needed to use mapdict for a user subclass at all.
    # This immediately makes slots possible.

    # assumes presence of _get_mapdict_map, _set_mapdict_map
    # _mapdict_init_empty, _mapdict_read_storage,
    # _mapdict_write_storage, _mapdict_storage_length,
    # _set_mapdict_storage_and_map

    # _____________________________________________
    # objspace interface

    # class access

    def getclass(self, space):
        return self._get_mapdict_map().terminator.w_cls

    def setclass(self, space, w_cls):
        new_obj = self._get_mapdict_map().set_terminator(self, w_cls.terminator)
        self._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)

    def user_setup(self, space, w_subtype):
        from pypy.module.__builtin__.interp_classobj import W_InstanceObject
        assert (not self.typedef.hasdict or
                isinstance(w_subtype.terminator, NoDictTerminator) or
                self.typedef is W_InstanceObject.typedef)
        self._mapdict_init_empty(w_subtype.terminator)


    # methods needed for slots

    def getslotvalue(self, slotindex):
        index = SLOTS_STARTING_FROM + slotindex
        return self._get_mapdict_map().read(self, "slot", index)

    def setslotvalue(self, slotindex, w_value):
        index = SLOTS_STARTING_FROM + slotindex
        self._get_mapdict_map().write(self, "slot", index, w_value)

    def delslotvalue(self, slotindex):
        index = SLOTS_STARTING_FROM + slotindex
        new_obj = self._get_mapdict_map().delete(self, "slot", index)
        if new_obj is None:
            return False
        self._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)
        return True


class MapdictWeakrefSupport(object):
    # stuff used by the _weakref implementation

    def getweakref(self):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        lifeline = self._get_mapdict_map().read(self, "weakref", SPECIAL)
        if lifeline is None:
            return None
        assert isinstance(lifeline, WeakrefLifeline)
        return lifeline
    getweakref._cannot_really_call_random_things_ = True

    def setweakref(self, space, weakreflifeline):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        assert isinstance(weakreflifeline, WeakrefLifeline)
        self._get_mapdict_map().write(self, "weakref", SPECIAL, weakreflifeline)
    setweakref._cannot_really_call_random_things_ = True

    def delweakref(self):
        self._get_mapdict_map().write(self, "weakref", SPECIAL, None)
    delweakref._cannot_really_call_random_things_ = True


class MapdictDictSupport(object):

    # objspace interface for dictionary operations

    def getdictvalue(self, space, attrname):
        return self._get_mapdict_map().read(self, attrname, DICT)

    def setdictvalue(self, space, attrname, w_value):
        return self._get_mapdict_map().write(self, attrname, DICT, w_value)

    def deldictvalue(self, space, attrname):
        new_obj = self._get_mapdict_map().delete(self, attrname, DICT)
        if new_obj is None:
            return False
        self._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)
        return True

    def getdict(self, space):
        return _obj_getdict(self, space)

    def setdict(self, space, w_dict):
        _obj_setdict(self, space, w_dict)

# a couple of helpers for the classes above, factored out to reduce
# the translated code size

@objectmodel.dont_inline
def _obj_getdict(self, space):
    terminator = self._get_mapdict_map().terminator
    assert isinstance(terminator, DictTerminator) or isinstance(terminator, DevolvedDictTerminator)
    w_dict = self._get_mapdict_map().read(self, "dict", SPECIAL)
    if w_dict is not None:
        assert isinstance(w_dict, W_DictMultiObject)
        return w_dict

    strategy = space.fromcache(MapDictStrategy)
    storage = strategy.erase(self)
    w_dict = W_DictObject(space, strategy, storage)
    flag = self._get_mapdict_map().write(self, "dict", SPECIAL, w_dict)
    assert flag
    return w_dict

@objectmodel.dont_inline
def _obj_setdict(self, space, w_dict):
    from pypy.interpreter.error import oefmt
    terminator = self._get_mapdict_map().terminator
    assert isinstance(terminator, DictTerminator) or isinstance(terminator, DevolvedDictTerminator)
    if not space.isinstance_w(w_dict, space.w_dict):
        raise oefmt(space.w_TypeError, "setting dictionary to a non-dict")
    assert isinstance(w_dict, W_DictMultiObject)
    w_olddict = self.getdict(space)
    assert isinstance(w_olddict, W_DictMultiObject)
    # The old dict has got 'self' as dstorage, but we are about to
    # change self's ("dict", SPECIAL) attribute to point to the
    # new dict.  If the old dict was using the MapDictStrategy, we
    # have to force it now: otherwise it would remain an empty
    # shell that continues to delegate to 'self'.
    if type(w_olddict.get_strategy()) is MapDictStrategy:
        w_olddict.get_strategy().switch_to_object_strategy(w_olddict)
    flag = self._get_mapdict_map().write(self, "dict", SPECIAL, w_dict)
    assert flag

class MapdictStorageMixin(object):
    def _get_mapdict_map(self):
        return jit.promote(self.map)
    def _set_mapdict_map(self, map):
        self.map = map

    def _mapdict_init_empty(self, map):
        from rpython.rlib.debug import make_sure_not_resized
        self.map = map
        self.storage = make_sure_not_resized([None] * map.size_estimate())

    def _mapdict_read_storage(self, storageindex):
        assert storageindex >= 0
        return self.storage[storageindex]

    def _mapdict_write_storage(self, storageindex, value):
        self.storage[storageindex] = value

    def _mapdict_storage_length(self):
        return len(self.storage)

    def _set_mapdict_storage_and_map(self, storage, map):
        self.storage = storage
        self.map = map

class ObjectWithoutDict(W_Root):
    # mainly for tests
    objectmodel.import_from_mixin(MapdictStorageMixin)

    objectmodel.import_from_mixin(BaseUserClassMapdict)
    objectmodel.import_from_mixin(MapdictWeakrefSupport)


class Object(W_Root):
    # mainly for tests
    objectmodel.import_from_mixin(MapdictStorageMixin)

    objectmodel.import_from_mixin(BaseUserClassMapdict)
    objectmodel.import_from_mixin(MapdictWeakrefSupport)
    objectmodel.import_from_mixin(MapdictDictSupport)


SUBCLASSES_NUM_FIELDS = 5

def _make_storage_mixin_size_n(n=SUBCLASSES_NUM_FIELDS):
    from rpython.rlib import unroll
    rangen = unroll.unrolling_iterable(range(n))
    nmin1 = n - 1
    rangenmin1 = unroll.unrolling_iterable(range(nmin1))
    valnmin1 = "_value%s" % nmin1
    class subcls(object):
        def _get_mapdict_map(self):
            return jit.promote(self.map)
        def _set_mapdict_map(self, map):
            self.map = map
        def _mapdict_init_empty(self, map):
            for i in rangenmin1:
                setattr(self, "_value%s" % i, None)
            setattr(self, valnmin1, erase_item(None))
            self.map = map

        def _has_storage_list(self):
            return self.map.length() > n

        def _mapdict_get_storage_list(self):
            erased = getattr(self, valnmin1)
            return unerase_list(erased)

        def _mapdict_read_storage(self, storageindex):
            assert storageindex >= 0
            if storageindex < nmin1:
                for i in rangenmin1:
                    if storageindex == i:
                        return getattr(self, "_value%s" % i)
            if self._has_storage_list():
                return self._mapdict_get_storage_list()[storageindex - nmin1]
            erased = getattr(self, "_value%s" % nmin1)
            return unerase_item(erased)

        def _mapdict_write_storage(self, storageindex, value):
            for i in rangenmin1:
                if storageindex == i:
                    setattr(self, "_value%s" % i, value)
                    return
            if self._has_storage_list():
                self._mapdict_get_storage_list()[storageindex - nmin1] = value
                return
            setattr(self, "_value%s" % nmin1, erase_item(value))

        def _mapdict_storage_length(self):
            if self._has_storage_list():
                return len(self._mapdict_get_storage_list()) + (n - 1)
            return n

        def _set_mapdict_storage_and_map(self, storage, map):
            self.map = map
            len_storage = len(storage)
            for i in rangenmin1:
                if i < len_storage:
                    erased = storage[i]
                else:
                    erased = None
                setattr(self, "_value%s" % i, erased)
            has_storage_list = self._has_storage_list()
            if len_storage < n:
                assert not has_storage_list
                erased = erase_item(None)
            elif len_storage == n:
                assert not has_storage_list
                erased = erase_item(storage[nmin1])
            elif not has_storage_list:
                # storage is longer than self.map.length() only due to
                # overallocation
                erased = erase_item(storage[nmin1])
                # in theory, we should be ultra-paranoid and check all entries,
                # but checking just one should catch most problems anyway:
                assert storage[n] is None
            else:
                storage_list = storage[nmin1:]
                erased = erase_list(storage_list)
            setattr(self, "_value%s" % nmin1, erased)

    subcls.__name__ = "Size%s" % n
    return subcls

# ____________________________________________________________
# dict implementation

def get_terminator_for_dicts(space):
    return DictTerminator(space, None)

class MapDictStrategy(DictStrategy):

    erase, unerase = rerased.new_erasing_pair("map")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def __init__(self, space):
        self.space = space

    def get_empty_storage(self):
        w_result = Object()
        terminator = self.space.fromcache(get_terminator_for_dicts)
        w_result._mapdict_init_empty(terminator)
        return self.erase(w_result)

    def switch_to_object_strategy(self, w_dict):
        w_obj = self.unerase(w_dict.dstorage)
        strategy = self.space.fromcache(ObjectDictStrategy)
        dict_w = strategy.unerase(strategy.get_empty_storage())
        w_dict.set_strategy(strategy)
        w_dict.dstorage = strategy.erase(dict_w)
        assert w_obj.getdict(self.space) is w_dict or w_obj._get_mapdict_map().terminator.w_cls is None
        materialize_r_dict(self.space, w_obj, dict_w)

    def getitem(self, w_dict, w_key):
        space = self.space
        w_lookup_type = space.type(w_key)
        if space.is_w(w_lookup_type, space.w_str):
            return self.getitem_str(w_dict, space.str_w(w_key))
        elif _never_equal_to_string(space, w_lookup_type):
            return None
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.getitem(w_key)

    def getitem_str(self, w_dict, key):
        w_obj = self.unerase(w_dict.dstorage)
        return w_obj.getdictvalue(self.space, key)

    def setitem_str(self, w_dict, key, w_value):
        w_obj = self.unerase(w_dict.dstorage)
        flag = w_obj.setdictvalue(self.space, key, w_value)
        assert flag

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.setitem_str(w_dict, self.space.str_w(w_key), w_value)
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.setitem(w_key, w_value)

    def setdefault(self, w_dict, w_key, w_default):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            key = space.str_w(w_key)
            w_result = self.getitem_str(w_dict, key)
            if w_result is not None:
                return w_result
            self.setitem_str(w_dict, key, w_default)
            return w_default
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.setdefault(w_key, w_default)

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        w_obj = self.unerase(w_dict.dstorage)
        if space.is_w(w_key_type, space.w_str):
            key = self.space.str_w(w_key)
            flag = w_obj.deldictvalue(space, key)
            if not flag:
                raise KeyError
        elif _never_equal_to_string(space, w_key_type):
            raise KeyError
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.delitem(w_key)

    def length(self, w_dict):
        res = 0
        curr = self.unerase(w_dict.dstorage)._get_mapdict_map().search(DICT)
        while curr is not None:
            curr = curr.back
            curr = curr.search(DICT)
            res += 1
        return res

    def clear(self, w_dict):
        w_obj = self.unerase(w_dict.dstorage)
        new_obj = w_obj._get_mapdict_map().remove_dict_entries(w_obj)
        w_obj._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)

    def popitem(self, w_dict):
        curr = self.unerase(w_dict.dstorage)._get_mapdict_map().search(DICT)
        if curr is None:
            raise KeyError
        key = curr.name
        w_value = self.getitem_str(w_dict, key)
        w_key = self.space.wrap(key)
        self.delitem(w_dict, w_key)
        return (w_key, w_value)

    # XXX could implement a more efficient w_keys based on space.newlist_bytes

    def iterkeys(self, w_dict):
        return MapDictIteratorKeys(self.space, self, w_dict)
    def itervalues(self, w_dict):
        return MapDictIteratorValues(self.space, self, w_dict)
    def iteritems(self, w_dict):
        return MapDictIteratorItems(self.space, self, w_dict)


def materialize_r_dict(space, obj, dict_w):
    map = obj._get_mapdict_map()
    new_obj = map.materialize_r_dict(space, obj, dict_w)
    obj._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)

class MapDictIteratorKeys(BaseKeyIterator):
    def __init__(self, space, strategy, w_dict):
        BaseKeyIterator.__init__(self, space, strategy, w_dict)
        w_obj = strategy.unerase(w_dict.dstorage)
        self.w_obj = w_obj
        self.orig_map = self.curr_map = w_obj._get_mapdict_map()

    def next_key_entry(self):
        assert isinstance(self.w_dict.get_strategy(), MapDictStrategy)
        if self.orig_map is not self.w_obj._get_mapdict_map():
            return None
        if self.curr_map:
            curr_map = self.curr_map.search(DICT)
            if curr_map:
                self.curr_map = curr_map.back
                attr = curr_map.name
                w_attr = self.space.wrap(attr)
                return w_attr
        return None


class MapDictIteratorValues(BaseValueIterator):
    def __init__(self, space, strategy, w_dict):
        BaseValueIterator.__init__(self, space, strategy, w_dict)
        w_obj = strategy.unerase(w_dict.dstorage)
        self.w_obj = w_obj
        self.orig_map = self.curr_map = w_obj._get_mapdict_map()

    def next_value_entry(self):
        assert isinstance(self.w_dict.get_strategy(), MapDictStrategy)
        if self.orig_map is not self.w_obj._get_mapdict_map():
            return None
        if self.curr_map:
            curr_map = self.curr_map.search(DICT)
            if curr_map:
                self.curr_map = curr_map.back
                attr = curr_map.name
                return self.w_obj.getdictvalue(self.space, attr)
        return None


class MapDictIteratorItems(BaseItemIterator):
    def __init__(self, space, strategy, w_dict):
        BaseItemIterator.__init__(self, space, strategy, w_dict)
        w_obj = strategy.unerase(w_dict.dstorage)
        self.w_obj = w_obj
        self.orig_map = self.curr_map = w_obj._get_mapdict_map()

    def next_item_entry(self):
        assert isinstance(self.w_dict.get_strategy(), MapDictStrategy)
        if self.orig_map is not self.w_obj._get_mapdict_map():
            return None, None
        if self.curr_map:
            curr_map = self.curr_map.search(DICT)
            if curr_map:
                self.curr_map = curr_map.back
                attr = curr_map.name
                w_attr = self.space.wrap(attr)
                return w_attr, self.w_obj.getdictvalue(self.space, attr)
        return None, None


# ____________________________________________________________
# Magic caching

class CacheEntry(object):
    version_tag = None
    storageindex = 0
    w_method = None # for callmethod
    success_counter = 0
    failure_counter = 0

    def is_valid_for_obj(self, w_obj):
        map = w_obj._get_mapdict_map()
        return self.is_valid_for_map(map)

    @jit.dont_look_inside
    def is_valid_for_map(self, map):
        # note that 'map' can be None here
        mymap = self.map_wref()
        if mymap is not None and mymap is map:
            version_tag = map.terminator.w_cls.version_tag()
            if version_tag is self.version_tag:
                # everything matches, it's incredibly fast
                if map.space.config.objspace.std.withmethodcachecounter:
                    self.success_counter += 1
                return True
        return False

_invalid_cache_entry_map = objectmodel.instantiate(AbstractAttribute)
_invalid_cache_entry_map.terminator = None
INVALID_CACHE_ENTRY = CacheEntry()
INVALID_CACHE_ENTRY.map_wref = weakref.ref(_invalid_cache_entry_map)
                                 # different from any real map ^^^

def init_mapdict_cache(pycode):
    num_entries = len(pycode.co_names_w)
    pycode._mapdict_caches = [INVALID_CACHE_ENTRY] * num_entries

@jit.dont_look_inside
def _fill_cache(pycode, nameindex, map, version_tag, storageindex, w_method=None):
    entry = pycode._mapdict_caches[nameindex]
    if entry is INVALID_CACHE_ENTRY:
        entry = CacheEntry()
        pycode._mapdict_caches[nameindex] = entry
    entry.map_wref = weakref.ref(map)
    entry.version_tag = version_tag
    entry.storageindex = storageindex
    entry.w_method = w_method
    if pycode.space.config.objspace.std.withmethodcachecounter:
        entry.failure_counter += 1

def LOAD_ATTR_caching(pycode, w_obj, nameindex):
    # this whole mess is to make the interpreter quite a bit faster; it's not
    # used if we_are_jitted().
    entry = pycode._mapdict_caches[nameindex]
    map = w_obj._get_mapdict_map()
    if entry.is_valid_for_map(map) and entry.w_method is None:
        # everything matches, it's incredibly fast
        return w_obj._mapdict_read_storage(entry.storageindex)
    return LOAD_ATTR_slowpath(pycode, w_obj, nameindex, map)
LOAD_ATTR_caching._always_inline_ = True

def LOAD_ATTR_slowpath(pycode, w_obj, nameindex, map):
    space = pycode.space
    w_name = pycode.co_names_w[nameindex]
    if map is not None:
        w_type = map.terminator.w_cls
        w_descr = w_type.getattribute_if_not_from_object()
        if w_descr is not None:
            return space._handle_getattribute(w_descr, w_obj, w_name)
        version_tag = w_type.version_tag()
        if version_tag is not None:
            name = space.str_w(w_name)
            # We need to care for obscure cases in which the w_descr is
            # a MutableCell, which may change without changing the version_tag
            _, w_descr = w_type._pure_lookup_where_with_method_cache(
                name, version_tag)
            #
            attrname, index = ("", INVALID)
            if w_descr is None:
                attrname, index = (name, DICT) # common case: no such attr in the class
            elif isinstance(w_descr, MutableCell):
                pass              # we have a MutableCell in the class: give up
            elif space.is_data_descr(w_descr):
                # we have a data descriptor, which means the dictionary value
                # (if any) has no relevance.
                from pypy.interpreter.typedef import Member
                if isinstance(w_descr, Member):    # it is a slot -- easy case
                    attrname, index = ("slot", SLOTS_STARTING_FROM + w_descr.index)
            else:
                # There is a non-data descriptor in the class.  If there is
                # also a dict attribute, use the latter, caching its storageindex.
                # If not, we loose.  We could do better in this case too,
                # but we don't care too much; the common case of a method
                # invocation is handled by LOOKUP_METHOD_xxx below.
                attrname = name
                index = DICT
            #
            if index != INVALID:
                attr = map.find_map_attr(attrname, index)
                if attr is not None:
                    # Note that if map.terminator is a DevolvedDictTerminator,
                    # map.find_map_attr will always return None if index==DICT.
                    _fill_cache(pycode, nameindex, map, version_tag, attr.storageindex)
                    return w_obj._mapdict_read_storage(attr.storageindex)
    if space.config.objspace.std.withmethodcachecounter:
        INVALID_CACHE_ENTRY.failure_counter += 1
    return space.getattr(w_obj, w_name)
LOAD_ATTR_slowpath._dont_inline_ = True

def LOOKUP_METHOD_mapdict(f, nameindex, w_obj):
    pycode = f.getcode()
    entry = pycode._mapdict_caches[nameindex]
    if entry.is_valid_for_obj(w_obj):
        w_method = entry.w_method
        if w_method is not None:
            f.pushvalue(w_method)
            f.pushvalue(w_obj)
            return True
    return False

def LOOKUP_METHOD_mapdict_fill_cache_method(space, pycode, name, nameindex,
                                            w_obj, w_type, w_method):
    if w_method is None or isinstance(w_method, MutableCell):
        # don't cache the MutableCell XXX could be fixed
        return
    version_tag = w_type.version_tag()
    assert version_tag is not None
    map = w_obj._get_mapdict_map()
    if map is None or isinstance(map.terminator, DevolvedDictTerminator):
        return
    _fill_cache(pycode, nameindex, map, version_tag, -1, w_method)

# XXX fix me: if a function contains a loop with both LOAD_ATTR and
# XXX LOOKUP_METHOD on the same attribute name, it keeps trashing and
# XXX rebuilding the cache
