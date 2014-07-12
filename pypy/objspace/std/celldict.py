""" A very simple cell dict implementation using a version tag. The dictionary
maps keys to objects. If a specific key is changed a lot, a level of
indirection is introduced to make the version tag change less often.
"""

from rpython.rlib import jit, rerased

from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.dictmultiobject import (
    DictStrategy, ObjectDictStrategy, _never_equal_to_string,
    create_iterator_classes)


class VersionTag(object):
    pass


class ModuleCell(W_Root):
    def __init__(self, w_value):
        self.w_value = w_value

    def __repr__(self):
        return "<ModuleCell: %s>" % (self.w_value, )


def unwrap_cell(w_value):
    if isinstance(w_value, ModuleCell):
        return w_value.w_value
    return w_value


def _wrapkey(space, key):
    return space.wrap(key.decode('utf-8'))


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
        # A mutation means changing an existing key to point to a new value.
        # A value is either a regular wrapped object, or a ModuleCell if we
        # detect mutations.  It means that each existing key can only trigger
        # a mutation at most once.
        self.version = VersionTag()

    def dictvalue_no_unwrapping(self, w_dict, key):
        # NB: it's important to promote self here, so that self.version is a
        # no-op due to the quasi-immutable field
        self = jit.promote(self)
        return self._dictvalue_no_unwrapping_pure(self.version, w_dict, key)

    @jit.elidable_promote('0,1,2')
    def _dictvalue_no_unwrapping_pure(self, version, w_dict, key):
        # may raise KeyError.  If it does, then the JIT is prevented from
        # considering this function as elidable.  This is what lets us add
        # new keys to the dictionary without changing the version.
        return self.unerase(w_dict.dstorage)[key]

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_unicode):
            self.setitem_str(w_dict, space.str_w(w_key), w_value)
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.setitem(w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        try:
            cell = self.dictvalue_no_unwrapping(w_dict, key)
        except KeyError:
            pass
        else:
            if isinstance(cell, ModuleCell):
                cell.w_value = w_value
                return
            # If the new value and the current value are the same, don't
            # create a level of indirection, or mutate the version.
            if self.space.is_w(w_value, cell):
                return
            w_value = ModuleCell(w_value)
            self.mutated()
        self.unerase(w_dict.dstorage)[key] = w_value

    def setdefault(self, w_dict, w_key, w_default):
        space = self.space
        if space.is_w(space.type(w_key), space.w_unicode):
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
        if space.is_w(w_key_type, space.w_unicode):
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
        if space.is_w(w_lookup_type, space.w_unicode):
            return self.getitem_str(w_dict, space.str_w(w_key))

        elif _never_equal_to_string(space, w_lookup_type):
            return None
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.getitem(w_key)

    def getitem_str(self, w_dict, key):
        try:
            cell = self.dictvalue_no_unwrapping(w_dict, key)
        except KeyError:
            return None
        return unwrap_cell(cell)

    def w_keys(self, w_dict):
        space = self.space
        l = self.unerase(w_dict.dstorage).keys()
        return space.newlist_bytes(l)

    def values(self, w_dict):
        iterator = self.unerase(w_dict.dstorage).itervalues
        return [unwrap_cell(cell) for cell in iterator()]

    def items(self, w_dict):
        space = self.space
        iterator = self.unerase(w_dict.dstorage).iteritems
        return [space.newtuple([_wrapkey(space, key), unwrap_cell(cell)])
                for key, cell in iterator()]

    def clear(self, w_dict):
        self.unerase(w_dict.dstorage).clear()
        self.mutated()

    def popitem(self, w_dict):
        space = self.space
        d = self.unerase(w_dict.dstorage)
        key, cell = d.popitem()
        self.mutated()
        return _wrapkey(space, key), unwrap_cell(cell)

    def switch_to_object_strategy(self, w_dict):
        space = self.space
        d = self.unerase(w_dict.dstorage)
        strategy = space.fromcache(ObjectDictStrategy)
        d_new = strategy.unerase(strategy.get_empty_storage())
        for key, cell in d.iteritems():
            d_new[_wrapkey(space, key)] = unwrap_cell(cell)
        w_dict.strategy = strategy
        w_dict.dstorage = strategy.erase(d_new)

    def getiterkeys(self, w_dict):
        return self.unerase(w_dict.dstorage).iterkeys()

    def getitervalues(self, w_dict):
        return self.unerase(w_dict.dstorage).itervalues()

    def getiteritems(self, w_dict):
        return self.unerase(w_dict.dstorage).iteritems()

    wrapkey = _wrapkey

    def wrapvalue(space, value):
        return unwrap_cell(value)


create_iterator_classes(ModuleDictStrategy)
