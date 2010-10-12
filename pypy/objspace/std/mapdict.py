from pypy.rlib import jit, objectmodel

from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.dictmultiobject import IteratorImplementation
from pypy.objspace.std.dictmultiobject import _is_sane_hash
from pypy.objspace.std.objectobject import W_ObjectObject

# ____________________________________________________________
# attribute shapes

NUM_DIGITS = 4

class AbstractAttribute(object):
    _immutable_fields_ = ['w_cls']
    cache_attrs = None
    _size_estimate = 0

    def __init__(self, space, w_cls):
        self.space = space
        self.w_cls = w_cls

    def read(self, obj, selector):
        raise NotImplementedError("abstract base class")

    def write(self, obj, selector, w_value):
        raise NotImplementedError("abstract base class")

    def delete(self, obj, selector):
        return None

    def index(self, selector):
        return -1

    def copy(self, obj):
        raise NotImplementedError("abstract base class")

    def length(self):
        raise NotImplementedError("abstract base class")

    def get_terminator(self):
        raise NotImplementedError("abstract base class")

    def set_terminator(self, obj, terminator):
        raise NotImplementedError("abstract base class")

    @jit.purefunction
    def size_estimate(self):
        return self._size_estimate >> NUM_DIGITS

    def search(self, attrtype):
        return None

    @jit.purefunction
    def _get_new_attr(self, name, index):
        selector = name, index
        cache = self.cache_attrs
        if cache is None:
            cache = self.cache_attrs = {}
        attr = cache.get(selector, None)
        if attr is None:
            attr = PlainAttribute(selector, self)
            cache[selector] = attr
        return attr

    @jit.unroll_safe
    def add_attr(self, obj, selector, w_value):
        # grumble, jit needs this
        attr = self._get_new_attr(selector[0], selector[1])
        oldattr = obj._get_mapdict_map()
        if not jit.we_are_jitted():
            oldattr._size_estimate += attr.size_estimate() - oldattr.size_estimate()
            assert oldattr.size_estimate() >= oldattr.length()
        if attr.length() > obj._mapdict_storage_length():
            # note that attr.size_estimate() is always at least attr.length()
            new_storage = [None] * attr.size_estimate()
            for i in range(obj._mapdict_storage_length()):
                new_storage[i] = obj._mapdict_read_storage(i)
            obj._set_mapdict_storage_and_map(new_storage, attr)

        # the order is important here: first change the map, then the storage,
        # for the benefit of the special subclasses
        obj._set_mapdict_map(attr)
        obj._mapdict_write_storage(attr.position, w_value)

    def materialize_r_dict(self, space, obj, w_d):
        raise NotImplementedError("abstract base class")

    def remove_dict_entries(self, obj):
        raise NotImplementedError("abstract base class")

    def __repr__(self):
        return "<%s w_cls=%s>" % (self.__class__.__name__, self.w_cls)


class Terminator(AbstractAttribute):

    def read(self, obj, selector):
        return None

    def write(self, obj, selector, w_value):
        obj._get_mapdict_map().add_attr(obj, selector, w_value)
        return True

    def copy(self, obj):
        result = Object()
        result.space = self.space
        result._init_empty(self)
        return result

    def length(self):
        return 0

    def get_terminator(self):
        return self

    def set_terminator(self, obj, terminator):
        result = Object()
        result.space = self.space
        result._init_empty(terminator)
        return result

    def remove_dict_entries(self, obj):
        return self.copy(obj)

class DictTerminator(Terminator):
    _immutable_fields_ = ['devolved_dict_terminator']
    def __init__(self, space, w_cls):
        Terminator.__init__(self, space, w_cls)
        self.devolved_dict_terminator = DevolvedDictTerminator(space, w_cls)

    def materialize_r_dict(self, space, obj, w_d):
        result = Object()
        result.space = space
        result._init_empty(self.devolved_dict_terminator)
        return result


class NoDictTerminator(Terminator):
    def write(self, obj, selector, w_value):
        if selector[1] == DICT:
            return False
        return Terminator.write(self, obj, selector, w_value)


class DevolvedDictTerminator(Terminator):
    def read(self, obj, selector):
        if selector[1] == DICT:
            w_dict = obj.getdict()
            space = self.space
            return space.finditem_str(w_dict, selector[0])
        return Terminator.read(self, obj, selector)

    def write(self, obj, selector, w_value):
        if selector[1] == DICT:
            w_dict = obj.getdict()
            space = self.space
            space.setitem_str(w_dict, selector[0], w_value)
            return True
        return Terminator.write(self, obj, selector, w_value)

    def delete(self, obj, selector):
        from pypy.interpreter.error import OperationError
        if selector[1] == DICT:
            w_dict = obj.getdict()
            space = self.space
            try:
                space.delitem(w_dict, space.wrap(selector[0]))
            except OperationError, ex:
                if not ex.match(space, space.w_KeyError):
                    raise
            return Terminator.copy(self, obj)
        return Terminator.delete(self, obj, selector)

    def remove_dict_entries(self, obj):
        assert 0, "should be unreachable"

    def set_terminator(self, obj, terminator):
        if not isinstance(terminator, DevolvedDictTerminator):
            assert isinstance(terminator, DictTerminator)
            terminator = terminator.devolved_dict_terminator
        return Terminator.set_terminator(self, obj, terminator)

class PlainAttribute(AbstractAttribute):
    _immutable_fields_ = ['selector', 'position', 'back']
    def __init__(self, selector, back):
        AbstractAttribute.__init__(self, back.space, back.w_cls)
        self.selector = selector
        self.position = back.length()
        self.back = back
        self._size_estimate = self.length() << NUM_DIGITS

    def _copy_attr(self, obj, new_obj):
        w_value = self.read(obj, self.selector)
        new_obj._get_mapdict_map().add_attr(new_obj, self.selector, w_value)

    def read(self, obj, selector):
        if selector == self.selector:
            return obj._mapdict_read_storage(self.position)
        return self.back.read(obj, selector)

    def write(self, obj, selector, w_value):
        if selector == self.selector:
            obj._mapdict_write_storage(self.position, w_value)
            return True
        return self.back.write(obj, selector, w_value)

    def delete(self, obj, selector):
        if selector == self.selector:
            # ok, attribute is deleted
            return self.back.copy(obj)
        new_obj = self.back.delete(obj, selector)
        if new_obj is not None:
            self._copy_attr(obj, new_obj)
        return new_obj

    def index(self, selector):
        if selector == self.selector:
            return self.position
        return self.back.index(selector)

    def copy(self, obj):
        new_obj = self.back.copy(obj)
        self._copy_attr(obj, new_obj)
        return new_obj

    def length(self):
        return self.position + 1

    def get_terminator(self):
        return self.back.get_terminator()

    def set_terminator(self, obj, terminator):
        new_obj = self.back.set_terminator(obj, terminator)
        self._copy_attr(obj, new_obj)
        return new_obj

    def search(self, attrtype):
        if self.selector[1] == attrtype:
            return self
        return self.back.search(attrtype)

    def materialize_r_dict(self, space, obj, w_d):
        new_obj = self.back.materialize_r_dict(space, obj, w_d)
        if self.selector[1] == DICT:
            w_attr = space.wrap(self.selector[0])
            w_d.r_dict_content[w_attr] = obj._mapdict_read_storage(self.position)
        else:
            self._copy_attr(obj, new_obj)
        return new_obj

    def remove_dict_entries(self, obj):
        new_obj = self.back.remove_dict_entries(obj)
        if self.selector[1] != DICT:
            self._copy_attr(obj, new_obj)
        return new_obj

    def __repr__(self):
        return "<PlainAttribute %s %s %r>" % (self.selector, self.position, self.back)

def _become(w_obj, new_obj):
    # this is like the _become method, really, but we cannot use that due to
    # RPython reasons
    w_obj._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)

# ____________________________________________________________
# object implementation

DICT = 0
SPECIAL = 1
INVALID = 2
SLOTS_STARTING_FROM = 3


class BaseMapdictObject: # slightly evil to make it inherit from W_Root
    _mixin_ = True

    def _init_empty(self, map):
        raise NotImplementedError("abstract base class")

    def _become(self, new_obj):
        self._set_mapdict_storage_and_map(new_obj.storage, new_obj.map)

    def _get_mapdict_map(self):
        return jit.hint(self.map, promote=True)
    def _set_mapdict_map(self, map):
        self.map = map
    # _____________________________________________
    # objspace interface

    def getdictvalue(self, space, attrname):
        return self._get_mapdict_map().read(self, (attrname, DICT))

    def setdictvalue(self, space, attrname, w_value, shadows_type=True):
        return self._get_mapdict_map().write(self, (attrname, DICT), w_value)

    def deldictvalue(self, space, w_name):
        attrname = space.str_w(w_name)
        new_obj = self._get_mapdict_map().delete(self, (attrname, DICT))
        if new_obj is None:
            return False
        self._become(new_obj)
        return True

    def getdict(self):
        w_dict = self._get_mapdict_map().read(self, ("dict", SPECIAL))
        if w_dict is not None:
            assert isinstance(w_dict, W_DictMultiObject)
            return w_dict
        w_dict = MapDictImplementation(self.space, self)
        flag = self._get_mapdict_map().write(self, ("dict", SPECIAL), w_dict)
        assert flag
        return w_dict

    def setdict(self, space, w_dict):
        from pypy.interpreter.typedef import check_new_dictionary
        w_dict = check_new_dictionary(space, w_dict)
        w_olddict = self.getdict()
        assert isinstance(w_dict, W_DictMultiObject)
        if w_olddict.r_dict_content is None:
            w_olddict._as_rdict()
        flag = self._get_mapdict_map().write(self, ("dict", SPECIAL), w_dict)
        assert flag

    def getclass(self, space):
        return self._get_mapdict_map().w_cls

    def setclass(self, space, w_cls):
        new_obj = self._get_mapdict_map().set_terminator(self, w_cls.terminator)
        self._become(new_obj)

    def user_setup(self, space, w_subtype):
        from pypy.module.__builtin__.interp_classobj import W_InstanceObject
        self.space = space
        assert (not self.typedef.hasdict or
                self.typedef is W_InstanceObject.typedef)
        self._init_empty(w_subtype.terminator)

    def getslotvalue(self, index):
        key = ("slot", SLOTS_STARTING_FROM + index)
        return self._get_mapdict_map().read(self, key)

    def setslotvalue(self, index, w_value):
        key = ("slot", SLOTS_STARTING_FROM + index)
        self._get_mapdict_map().write(self, key, w_value)

    # used by _weakref implemenation

    def getweakref(self):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        lifeline = self._get_mapdict_map().read(self, ("weakref", SPECIAL))
        if lifeline is None:
            return None
        assert isinstance(lifeline, WeakrefLifeline)
        return lifeline

    def setweakref(self, space, weakreflifeline):
        from pypy.module._weakref.interp__weakref import WeakrefLifeline
        assert isinstance(weakreflifeline, WeakrefLifeline)
        self._get_mapdict_map().write(self, ("weakref", SPECIAL), weakreflifeline)

class ObjectMixin(object):
    _mixin_ = True
    def _init_empty(self, map):
        from pypy.rlib.debug import make_sure_not_resized
        self.map = map
        self.storage = make_sure_not_resized([None] * map.size_estimate())

    def _mapdict_read_storage(self, index):
        return self.storage[index]
    def _mapdict_write_storage(self, index, value):
        self.storage[index] = value
    def _mapdict_storage_length(self):
        return len(self.storage)
    def _set_mapdict_storage_and_map(self, storage, map):
        self.storage = storage
        self.map = map

class Object(ObjectMixin, BaseMapdictObject, W_Root):
    pass # mainly for tests

def get_subclass_of_correct_size(space, cls, w_type):
    assert space.config.objspace.std.withmapdict
    map = w_type.terminator
    classes = memo_get_subclass_of_correct_size(space, cls)
    size = map.size_estimate()
    if not size:
        size = 1
    try:
        return classes[size - 1]
    except IndexError:
        return classes[-1]
get_subclass_of_correct_size._annspecialcase_ = "specialize:arg(1)"

NUM_SUBCLASSES = 10 # XXX tweak this number

def memo_get_subclass_of_correct_size(space, supercls):
    key = space, supercls
    try:
        return _subclass_cache[key]
    except KeyError:
        assert not hasattr(supercls, "__del__")
        result = []
        for i in range(1, NUM_SUBCLASSES+1):
            result.append(_make_subclass_size_n(supercls, i))
        _subclass_cache[key] = result
        return result
memo_get_subclass_of_correct_size._annspecialcase_ = "specialize:memo"
_subclass_cache = {}

def _make_subclass_size_n(supercls, n):
    from pypy.rlib import unroll, rerased
    rangen = unroll.unrolling_iterable(range(n))
    nmin1 = n - 1
    rangenmin1 = unroll.unrolling_iterable(range(nmin1))
    class subcls(ObjectMixin, BaseMapdictObject, supercls):
        def _init_empty(self, map):
            from pypy.rlib.debug import make_sure_not_resized
            for i in rangen:
                setattr(self, "_value%s" % i, rerased.erase(None))
            self.map = map

        def _has_storage_list(self):
            return self.map.length() > n

        def _mapdict_get_storage_list(self):
            erased = getattr(self, "_value%s" % nmin1)
            return rerased.unerase_fixedsizelist(erased, W_Root)

        def _mapdict_read_storage(self, index):
            for i in rangenmin1:
                if index == i:
                    erased = getattr(self, "_value%s" % i)
                    return rerased.unerase(erased, W_Root)
            if self._has_storage_list():
                return self._mapdict_get_storage_list()[index - nmin1]
            erased = getattr(self, "_value%s" % nmin1)
            return rerased.unerase(erased, W_Root)

        def _mapdict_write_storage(self, index, value):
            erased = rerased.erase(value)
            for i in rangenmin1:
                if index == i:
                    setattr(self, "_value%s" % i, erased)
                    return
            if self._has_storage_list():
                self._mapdict_get_storage_list()[index - nmin1] = value
                return
            setattr(self, "_value%s" % nmin1, erased)

        def _mapdict_storage_length(self):
            if self._has_storage_list():
                return len(self._mapdict_get_storage_list()) + n - 1
            return n

        def _set_mapdict_storage_and_map(self, storage, map):
            self.map = map
            len_storage = len(storage)
            for i in rangenmin1:
                if i < len_storage:
                    erased = rerased.erase(storage[i])
                else:
                    erased = rerased.erase(None)
                setattr(self, "_value%s" % i, erased)
            has_storage_list = self._has_storage_list()
            if len_storage < n:
                assert not has_storage_list
                erased = rerased.erase(None)
            elif len_storage == n:
                assert not has_storage_list
                erased = rerased.erase(storage[nmin1])
            elif not has_storage_list:
                # storage is longer than self.map.length() only due to
                # overallocation
                erased = rerased.erase(storage[nmin1])
                # in theory, we should be ultra-paranoid and check all entries,
                # but checking just one should catch most problems anyway:
                assert storage[n] is None
            else:
                storage_list = storage[nmin1:]
                erased = rerased.erase_fixedsizelist(storage_list, W_Root)
            setattr(self, "_value%s" % nmin1, erased)

    subcls.__name__ = supercls.__name__ + "Size%s" % n
    return subcls

# ____________________________________________________________
# dict implementation


class MapDictImplementation(W_DictMultiObject):
    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def impl_getitem(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.impl_getitem_str(space.str_w(w_lookup))
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().impl_fallback_getitem(w_lookup)

    def impl_getitem_str(self, key):
        return self.w_obj.getdictvalue(self.space, key)

    def impl_setitem_str(self,  key, w_value, shadows_type=True):
        flag = self.w_obj.setdictvalue(self.space, key, w_value, shadows_type)
        assert flag

    def impl_setitem(self,  w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            self._as_rdict().impl_fallback_setitem(w_key, w_value)

    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            flag = self.w_obj.deldictvalue(space, w_key)
            if not flag:
                raise KeyError
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().impl_fallback_delitem(w_key)

    def impl_length(self):
        res = 0
        curr = self.w_obj._get_mapdict_map().search(DICT)
        while curr is not None:
            curr = curr.back
            curr = curr.search(DICT)
            res += 1
        return res

    def impl_iter(self):
        return MapDictIteratorImplementation(self.space, self)

    def impl_clear(self):
        w_obj = self.w_obj
        new_obj = w_obj._get_mapdict_map().remove_dict_entries(w_obj)
        _become(w_obj, new_obj)

    def _clear_fields(self):
        self.w_obj = None

    def _as_rdict(self):
        self.initialize_as_rdict()
        space = self.space
        w_obj = self.w_obj
        materialize_r_dict(space, w_obj, self)
        self._clear_fields()
        return self


def materialize_r_dict(space, obj, w_d):
    map = obj._get_mapdict_map()
    assert obj.getdict() is w_d
    new_obj = map.materialize_r_dict(space, obj, w_d)
    _become(obj, new_obj)

class MapDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        w_obj = dictimplementation.w_obj
        self.w_obj = w_obj
        self.orig_map = self.curr_map = w_obj._get_mapdict_map()

    def next_entry(self):
        implementation = self.dictimplementation
        assert isinstance(implementation, MapDictImplementation)
        if self.orig_map is not self.w_obj._get_mapdict_map():
            return None, None
        if self.curr_map:
            curr_map = self.curr_map.search(DICT)
            if curr_map:
                self.curr_map = curr_map.back
                attr = curr_map.selector[0]
                w_attr = self.space.wrap(attr)
                return w_attr, self.w_obj.getdictvalue(self.space, attr)
        return None, None

# ____________________________________________________________
# Magic caching

# XXX we also would like getdictvalue_attr_is_in_class() above

class CacheEntry(object):
    map = None
    version_tag = None
    index = 0
    success_counter = 0
    failure_counter = 0

INVALID_CACHE_ENTRY = CacheEntry()
INVALID_CACHE_ENTRY.map = objectmodel.instantiate(AbstractAttribute)
                             # different from any real map ^^^
INVALID_CACHE_ENTRY.map.w_cls = None

def init_mapdict_cache(pycode):
    num_entries = len(pycode.co_names_w)
    pycode._mapdict_caches = [INVALID_CACHE_ENTRY] * num_entries

def LOAD_ATTR_caching(pycode, w_obj, nameindex):
    # this whole mess is to make the interpreter quite a bit faster; it's not
    # used if we_are_jitted().
    entry = pycode._mapdict_caches[nameindex]
    map = w_obj._get_mapdict_map()
    if map is entry.map:
        version_tag = map.w_cls.version_tag()
        if version_tag is entry.version_tag:
            # everything matches, it's incredibly fast
            if pycode.space.config.objspace.std.withmethodcachecounter:
                entry.success_counter += 1
            return w_obj._mapdict_read_storage(entry.index)
    return LOAD_ATTR_slowpath(pycode, w_obj, nameindex, map)
LOAD_ATTR_caching._always_inline_ = True

def LOAD_ATTR_slowpath(pycode, w_obj, nameindex, map):
    space = pycode.space
    w_name = pycode.co_names_w[nameindex]
    if map is not None:
        w_type = map.w_cls
        w_descr = w_type.getattribute_if_not_from_object()
        if w_descr is not None:
            return space._handle_getattribute(w_descr, w_obj, w_name)

        version_tag = w_type.version_tag()
        if version_tag is not None:
            name = space.str_w(w_name)
            w_descr = w_type.lookup(name)
            selector = ("", INVALID)
            if w_descr is not None and space.is_data_descr(w_descr):
                from pypy.interpreter.typedef import Member
                descr = space.interpclass_w(w_descr)
                if isinstance(descr, Member):
                    selector = ("slot", SLOTS_STARTING_FROM + descr.index)
            else:
                selector = (name, DICT)
            if selector[1] != INVALID:
                index = map.index(selector)
                if index >= 0:
                    entry = pycode._mapdict_caches[nameindex]
                    if entry is INVALID_CACHE_ENTRY:
                        entry = CacheEntry()
                        pycode._mapdict_caches[nameindex] = entry
                    entry.map = map
                    entry.version_tag = version_tag
                    entry.index = index
                    if space.config.objspace.std.withmethodcachecounter:
                        entry.failure_counter += 1
                    return w_obj._mapdict_read_storage(index)
    if space.config.objspace.std.withmethodcachecounter:
        INVALID_CACHE_ENTRY.failure_counter += 1
    return space.getattr(w_obj, w_name)
LOAD_ATTR_slowpath._dont_inline_ = True
