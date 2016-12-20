"""dict implementation specialized for keyword argument dicts.

Based on two lists containing unwrapped key value pairs.
"""

from rpython.rlib import jit, rerased, objectmodel

from pypy.objspace.std.dictmultiobject import (
    BytesDictStrategy, DictStrategy, EmptyDictStrategy, ObjectDictStrategy,
    create_iterator_classes)


def _wrapkey(space, key):
    return space.newtext(key)


class EmptyKwargsDictStrategy(EmptyDictStrategy):
    def switch_to_bytes_strategy(self, w_dict):
        strategy = self.space.fromcache(KwargsDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.set_strategy(strategy)
        w_dict.dstorage = storage


class KwargsDictStrategy(DictStrategy):
    erase, unerase = rerased.new_erasing_pair("kwargsdict")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def wrap(self, key):
        return _wrapkey(self.space, key)

    def unwrap(self, wrapped):
        return self.space.text_w(wrapped)

    def get_empty_storage(self):
        d = ([], [])
        return self.erase(d)

    def is_correct_type(self, w_obj):
        space = self.space
        return space.is_w(space.type(w_obj), space.w_text)

    def _never_equal_to(self, w_lookup_type):
        return False

    def setitem(self, w_dict, w_key, w_value):
        if self.is_correct_type(w_key):
            self.setitem_str(w_dict, self.unwrap(w_key), w_value)
            return
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.setitem(w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        self._setitem_str_indirection(w_dict, key, w_value)

    @jit.look_inside_iff(lambda self, w_dict, key, w_value:
            jit.isconstant(self.length(w_dict)) and jit.isconstant(key))
    def _setitem_str_indirection(self, w_dict, key, w_value):
        keys, values_w = self.unerase(w_dict.dstorage)
        for i in range(len(keys)):
            if keys[i] == key:
                values_w[i] = w_value
                break
        else:
            # limit the size so that the linear searches don't become too long
            if len(keys) >= 16:
                self.switch_to_bytes_strategy(w_dict)
                w_dict.setitem_str(key, w_value)
            else:
                keys.append(key)
                values_w.append(w_value)

    def setdefault(self, w_dict, w_key, w_default):
        if self.is_correct_type(w_key):
            key = self.unwrap(w_key)
            w_result = self.getitem_str(w_dict, key)
            if w_result is not None:
                return w_result
            self.setitem_str(w_dict, key, w_default)
            return w_default
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.setdefault(w_key, w_default)

    def delitem(self, w_dict, w_key):
        # XXX could do better, but is it worth it?
        self.switch_to_object_strategy(w_dict)
        return w_dict.delitem(w_key)

    def length(self, w_dict):
        return len(self.unerase(w_dict.dstorage)[0])

    def getitem_str(self, w_dict, key):
        return self._getitem_str_indirection(w_dict, key)

    @jit.look_inside_iff(lambda self, w_dict, key:
            jit.isconstant(self.length(w_dict)) and jit.isconstant(key))
    def _getitem_str_indirection(self, w_dict, key):
        keys, values_w = self.unerase(w_dict.dstorage)
        for i in range(len(keys)):
            if keys[i] == key:
                return values_w[i]
        return None

    def getitem(self, w_dict, w_key):
        space = self.space
        if self.is_correct_type(w_key):
            return self.getitem_str(w_dict, self.unwrap(w_key))
        elif self._never_equal_to(space.type(w_key)):
            return None
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.getitem(w_key)

    def w_keys(self, w_dict):
        l = self.unerase(w_dict.dstorage)[0]
        return self.space.newlist_text(l[:])

    def values(self, w_dict):
        return self.unerase(w_dict.dstorage)[1][:] # to make non-resizable

    def items(self, w_dict):
        space = self.space
        keys, values_w = self.unerase(w_dict.dstorage)
        return [space.newtuple([self.wrap(keys[i]), values_w[i]])
                for i in range(len(keys))]

    def popitem(self, w_dict):
        keys, values_w = self.unerase(w_dict.dstorage)
        key = keys.pop()
        w_value = values_w.pop()
        return self.wrap(key), w_value

    def clear(self, w_dict):
        w_dict.dstorage = self.get_empty_storage()

    def switch_to_object_strategy(self, w_dict):
        strategy = self.space.fromcache(ObjectDictStrategy)
        keys, values_w = self.unerase(w_dict.dstorage)
        d_new = strategy.unerase(strategy.get_empty_storage())
        for i in range(len(keys)):
            d_new[self.wrap(keys[i])] = values_w[i]
        w_dict.set_strategy(strategy)
        w_dict.dstorage = strategy.erase(d_new)

    def switch_to_bytes_strategy(self, w_dict):
        strategy = self.space.fromcache(BytesDictStrategy)
        keys, values_w = self.unerase(w_dict.dstorage)
        storage = strategy.get_empty_storage()
        d_new = strategy.unerase(storage)
        for i in range(len(keys)):
            d_new[keys[i]] = values_w[i]
        w_dict.set_strategy(strategy)
        w_dict.dstorage = storage

    def view_as_kwargs(self, w_dict):
        keys, values_w = self.unerase(w_dict.dstorage)
        return keys[:], values_w[:] # copy to make non-resizable

    def getiterkeys(self, w_dict):
        return iter(self.unerase(w_dict.dstorage)[0])

    def getitervalues(self, w_dict):
        return iter(self.unerase(w_dict.dstorage)[1])

    def getiteritems_with_hash(self, w_dict):
        keys, values_w = self.unerase(w_dict.dstorage)
        return ZipItemsWithHash(keys, values_w)

    wrapkey = _wrapkey


class ZipItemsWithHash(object):
    def __init__(self, list1, list2):
        assert len(list1) == len(list2)
        self.list1 = list1
        self.list2 = list2
        self.i = 0

    def __iter__(self):
        return self

    def next(self):
        i = self.i
        if i >= len(self.list1):
            raise StopIteration
        self.i = i + 1
        key = self.list1[i]
        return (key, self.list2[i], objectmodel.compute_hash(key))

create_iterator_classes(KwargsDictStrategy)
