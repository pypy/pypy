""" A very simple cell dict implementation using a version tag. The dictionary
maps keys to objects. If a specific key is changed a lot, a level of
indirection is introduced to make the version tag change less often.
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.dictmultiobject import IteratorImplementation
from pypy.objspace.std.dictmultiobject import DictStrategy, _never_equal_to_string
from pypy.objspace.std.dictmultiobject import ObjectDictStrategy
from pypy.rlib import jit, rerased

class VersionTag(object):
    pass

class ModuleCell(W_Root):
    def __init__(self, w_value=None):
        self.w_value = w_value

    def __repr__(self):
        return "<ModuleCell: %s>" % (self.w_value, )

def unwrap_cell(w_value):
    if isinstance(w_value, ModuleCell):
        return w_value.w_value
    return w_value

class ModuleDictStrategy(DictStrategy):

    erase, unerase = rerased.new_erasing_pair("modulecell")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    _immutable_fields_ = ["version?"]

    def __init__(self, space):
        self.space = space
        self.version = VersionTag()

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
        if space.is_w(space.type(w_key), space.w_str):
            self.setitem_str(w_dict, self.space.str_w(w_key), w_value)
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.setitem(w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        cell = self.getdictvalue_no_unwrapping(w_dict, key)
        if isinstance(cell, ModuleCell):
            cell.w_value = w_value
            return
        # If the new value and the current value are the same, don't create a
        # level of indirection, or mutate are version.
        if self.space.is_w(w_value, cell):
            return
        if cell is not None:
            w_value = ModuleCell(w_value)
        self.mutated()
        self.unerase(w_dict.dstorage)[key] = w_value

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
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            dict_w = self.unerase(w_dict.dstorage)
            try:
                del dict_w[key]
            except KeyError:
                raise
            else:
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
        if space.is_w(w_lookup_type, space.w_str):
            return self.getitem_str(w_dict, space.str_w(w_key))

        elif _never_equal_to_string(space, w_lookup_type):
            return None
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.getitem(w_key)

    def getitem_str(self, w_dict, key):
        w_res = self.getdictvalue_no_unwrapping(w_dict, key)
        return unwrap_cell(w_res)

    def iter(self, w_dict):
        return ModuleDictIteratorImplementation(self.space, self, w_dict)

    def keys(self, w_dict):
        space = self.space
        iterator = self.unerase(w_dict.dstorage).iteritems
        return [space.wrap(key) for key, cell in iterator()]

    def values(self, w_dict):
        iterator = self.unerase(w_dict.dstorage).itervalues
        return [unwrap_cell(cell) for cell in iterator()]

    def items(self, w_dict):
        space = self.space
        iterator = self.unerase(w_dict.dstorage).iteritems
        return [space.newtuple([space.wrap(key), unwrap_cell(cell)])
                    for key, cell in iterator()]

    def clear(self, w_dict):
        iterator = self.unerase(w_dict.dstorage).clear()
        self.mutated()

    def popitem(self, w_dict):
        d = self.unerase(w_dict.dstorage)
        key, w_value = d.popitem()
        self.mutated()
        return self.space.wrap(key), unwrap_cell(w_value)

    def switch_to_object_strategy(self, w_dict):
        d = self.unerase(w_dict.dstorage)
        strategy = self.space.fromcache(ObjectDictStrategy)
        d_new = strategy.unerase(strategy.get_empty_storage())
        for key, cell in d.iteritems():
            d_new[self.space.wrap(key)] = unwrap_cell(cell)
        w_dict.strategy = strategy
        w_dict.dstorage = strategy.erase(d_new)

class ModuleDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, strategy, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        dict_w = strategy.unerase(dictimplementation.dstorage)
        self.iterator = dict_w.iteritems()

    def next_entry(self):
        for key, cell in self.iterator:
            return (self.space.wrap(key), unwrap_cell(cell))
        else:
            return None, None
