""" A very simple cell dict implementation using a version tag. The dictionary
maps keys to objects. If a specific key is changed a lot, a level of
indirection is introduced to make the version tag change less often.
"""
import weakref

from rpython.rlib import jit, rerased, objectmodel

from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.dictmultiobject import (
    DictStrategy, ObjectDictStrategy, _never_equal_to_string,
    create_iterator_classes, BytesDictStrategy,
    W_ModuleDictObject,
    W_DictObject)
from pypy.objspace.std.typeobject import (
    MutableCell, IntMutableCell, ObjectMutableCell, write_cell, unwrap_cell)


class VersionTag(object):
    pass


def _wrapkey(space, key):
    return space.newtext(key)


class ModuleDictStrategy(DictStrategy):

    erase, unerase = rerased.new_erasing_pair("modulecell")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    _immutable_fields_ = ["version?"]

    def __init__(self, space):
        self.space = space
        self.version = VersionTag()
        self.caches = None

    def get_empty_storage(self):
        return self.erase({})

    def mutated(self):
        self.version = VersionTag()

    def getdictvalue_no_unwrapping(self, w_dict, key):
        # NB: it's important to promote self here, so that self.version is a
        # no-op due to the quasi-immutable field
        self = jit.promote(self)
        return self._getdictvalue_no_unwrapping_pure(self.version, w_dict, key)

    @jit.elidable_promote('0,1,2')
    def _getdictvalue_no_unwrapping_pure(self, version, w_dict, key):
        return self.unerase(w_dict.dstorage).get(key, None)

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_text):
            self.setitem_str(w_dict, space.text_w(w_key), w_value)
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.setitem(w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        cell = self.getdictvalue_no_unwrapping(w_dict, key)
        return self._setitem_str_cell_known(cell, w_dict, key, w_value)

    def _setitem_str_cell_known(self, cell, w_dict, key, w_value):
        w_value = write_cell(self.space, cell, w_value)
        if w_value is None:
            return
        self.mutated()
        self.unerase(w_dict.dstorage)[key] = w_value
        if self.caches is None:
            return
        cache = self.caches.get(key, None)
        if cache:
            cache.cell = w_value

    def setdefault(self, w_dict, w_key, w_default):
        space = self.space
        if space.is_w(space.type(w_key), space.w_text):
            key = space.text_w(w_key)
            cell = self.getdictvalue_no_unwrapping(w_dict, key)
            w_result = unwrap_cell(self.space, cell)
            if w_result is not None:
                return w_result
            self._setitem_str_cell_known(cell, w_dict, key, w_default)
            return w_default
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.setdefault(w_key, w_default)

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_text):
            key = space.text_w(w_key)
            dict_w = self.unerase(w_dict.dstorage)
            try:
                del dict_w[key]
            except KeyError:
                raise
            else:
                if self.caches:
                    cache = self.caches.get(key, None)
                    if cache:
                        cache.cell = None
                self.mutated()
        elif _never_equal_to_string(space, w_key_type):
            raise KeyError
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.delitem(w_key)

    def length(self, w_dict):
        return len(self.unerase(w_dict.dstorage))

    def getitem(self, w_dict, w_key):
        space = self.space
        w_lookup_type = space.type(w_key)
        if space.is_w(w_lookup_type, space.w_text):
            return self.getitem_str(w_dict, space.text_w(w_key))

        elif _never_equal_to_string(space, w_lookup_type):
            return None
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.getitem(w_key)

    def getitem_str(self, w_dict, key):
        cell = self.getdictvalue_no_unwrapping(w_dict, key)
        return unwrap_cell(self.space, cell)

    def w_keys(self, w_dict):
        space = self.space
        l = self.unerase(w_dict.dstorage).keys()
        return space.newlist_text(l)

    def values(self, w_dict):
        iterator = self.unerase(w_dict.dstorage).itervalues
        return [unwrap_cell(self.space, cell) for cell in iterator()]

    def items(self, w_dict):
        space = self.space
        iterator = self.unerase(w_dict.dstorage).iteritems
        return [space.newtuple2(_wrapkey(space, key), unwrap_cell(self.space, cell))
                for key, cell in iterator()]

    def clear(self, w_dict):
        self.unerase(w_dict.dstorage).clear()
        self.mutated()

    def popitem(self, w_dict):
        space = self.space
        d = self.unerase(w_dict.dstorage)
        key, cell = d.popitem()
        self.mutated()
        return _wrapkey(space, key), unwrap_cell(self.space, cell)

    def switch_to_object_strategy(self, w_dict):
        space = self.space
        d = self.unerase(w_dict.dstorage)
        strategy = space.fromcache(ObjectDictStrategy)
        d_new = strategy.unerase(strategy.get_empty_storage())
        for key, cell in d.iteritems():
            d_new[_wrapkey(space, key)] = unwrap_cell(self.space, cell)
        if self.caches is not None:
            for cache in self.caches.itervalues():
                cache.cell = None
                cache.valid = False
            self.caches = None
        w_dict.set_strategy(strategy)
        w_dict.dstorage = strategy.erase(d_new)

    def getiterkeys(self, w_dict):
        return self.unerase(w_dict.dstorage).iterkeys()

    def getitervalues(self, w_dict):
        return self.unerase(w_dict.dstorage).itervalues()

    def getiteritems_with_hash(self, w_dict):
        return objectmodel.iteritems_with_hash(self.unerase(w_dict.dstorage))

    wrapkey = _wrapkey

    def wrapvalue(space, value):
        return unwrap_cell(space, value)

    def copy(self, w_dict):
        strategy = self.space.fromcache(BytesDictStrategy)
        str_dict = strategy.unerase(strategy.get_empty_storage())

        d = self.unerase(w_dict.dstorage)
        for key, cell in d.iteritems():
            str_dict[key] = unwrap_cell(self.space, cell)
        return W_DictObject(strategy.space, strategy, strategy.erase(str_dict))

    def get_global_cache(self, w_dict, key):
        space = w_dict.space
        if self.caches is None:
            cache = None
            self.caches = {}
        else:
            cache = self.caches.get(key, None)
        if cache is None:
            cell = self.getdictvalue_no_unwrapping(w_dict, key)
            cache = GlobalCache(cell)
            if (not space.config.objspace.honor__builtins__ and
                    cell is None and
                    w_dict is not space.builtin.w_dict):
                w_builtin_dict = space.builtin.w_dict
                assert isinstance(w_builtin_dict, W_ModuleDictObject)
                builtin_strategy = w_builtin_dict.mstrategy
                if isinstance(builtin_strategy, ModuleDictStrategy):
                    cell = builtin_strategy.getdictvalue_no_unwrapping(
                            w_builtin_dict, key)
                    # logic: if the global is not defined but the builtin is,
                    # cache it. otherwise don't cache the builtin ever
                    if cell is not None:
                        builtincache = builtin_strategy.get_global_cache(
                                w_builtin_dict, key)
                        cache.builtincache = builtincache
            self.caches[key] = cache
        return cache


create_iterator_classes(ModuleDictStrategy)



# ____________________________________________________________
# global caching

class GlobalCache(object):
    def __init__(self, cell):
        # works like this: self.cell is always the result of
        # getdictvalue_no_unwrapping on the equivalent key.
        # this means it is None if the key doesn't exist, a w_value if there is
        # no cell, or a Cell

        # if the module dict actually switches to a different strategy, then
        # cell is set to None, and valid to False
        self.cell = cell
        self.valid = True
        self.ref = weakref.ref(self)
        self.builtincache = None

    @objectmodel.always_inline
    def getvalue(self, space):
        return unwrap_cell(space, self.cell)

def LOAD_GLOBAL_cached(self, nameindex, next_instr):
    w_value = _LOAD_GLOBAL_cached(self, nameindex, next_instr)
    self.pushvalue(w_value)

@objectmodel.always_inline
def _LOAD_GLOBAL_cached(self, nameindex, next_instr):
    pycode = self.pycode
    if jit.we_are_jitted() or (
            self.debugdata is not None and
            self.debugdata.w_globals is not pycode.w_globals):
        varname = self.getname_u(nameindex)
        return _load_global_fallback(self, varname)
    cache_wref = pycode._globals_caches[nameindex]
    if cache_wref is not None:
        cache = cache_wref()
        if cache:
            w_value = cache.getvalue(self.space)
            if w_value is not None:
                return w_value
            if cache.valid:
                # the cache is valid. this means it's not in the globals
                # and we check the builtins next
                builtincache = cache.builtincache
                if builtincache is not None:
                    w_value = builtincache.getvalue(self.space)
                    if w_value is not None:
                        return w_value
                    varname = self.getname_u(nameindex)
                    w_value = self.get_builtin().getdictvalue(
                            self.space, varname)
                    if w_value is not None:
                        return w_value
                    else:
                        self._load_global_failed(varname)
    # either no cache or an invalid cache
    w_globals = pycode.w_globals
    varname = self.getname_u(nameindex)
    if isinstance(w_globals, W_ModuleDictObject):
        cache = w_globals.get_global_cache(varname)
        if cache is not None:
            assert cache.valid and cache.ref is not None
            pycode._globals_caches[nameindex] = cache.ref
    return _load_global_fallback(self, varname)

@objectmodel.dont_inline
def _load_global_fallback(self, varname):
    return self._load_global(varname)

def STORE_GLOBAL_cached(self, nameindex, next_instr):
    w_newvalue = self.popvalue()
    if jit.we_are_jitted() or self.getdebug() is not None:
        varname = self.getname_u(nameindex)
        self.space.setitem_str(self.get_w_globals(), varname, w_newvalue)
        return
    pycode = self.pycode
    cache_wref = pycode._globals_caches[nameindex]
    if cache_wref is not None:
        cache = cache_wref()
        if cache and cache.valid:
            w_value = write_cell(self.space, cache.cell, w_newvalue)
            if w_value is None:
                return

    varname = self.getname_u(nameindex)
    w_globals = self.pycode.w_globals
    self.space.setitem_str(w_globals, varname, w_newvalue)
    if isinstance(w_globals, W_ModuleDictObject):
        # the following can never be true, becaus W_ModuleDictObject can't be
        # user-subclassed, but let's be safe
        assert not w_globals.user_overridden_class
        cache = w_globals.get_global_cache(varname)
        if cache is not None:
            assert cache.valid and cache.ref is not None
            pycode._globals_caches[nameindex] = cache.ref

