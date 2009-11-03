from pypy.objspace.std.dictmultiobject import IteratorImplementation
from pypy.objspace.std.dictmultiobject import W_DictMultiObject, _is_sane_hash
from pypy.rlib.jit import purefunction, hint, we_are_jitted, unroll_safe
from pypy.rlib.rweakref import RWeakValueDictionary

NUM_DIGITS = 4

class SharedStructure(object):
    _immutable_fields_ = ["keys", "length", "back_struct", "other_structs",
                          "last_key"]

    def __init__(self, keys=None, length=0,
                 last_key=None,
                 back_struct=None):
        if keys is None:
            keys = {}
        self.keys = keys
        self.length = length
        self.back_struct = back_struct
        other_structs = RWeakValueDictionary(SharedStructure)
        self.other_structs = other_structs
        self.last_key = last_key
        self._size_estimate = length << NUM_DIGITS
        if last_key is not None:
            assert back_struct is not None

    def new_structure(self, added_key):
        keys = self.keys.copy()
        keys[added_key] = len(self.keys)
        new_structure = SharedStructure(keys, self.length + 1,
                                        added_key, self)
        self.other_structs.set(added_key, new_structure)
        return new_structure

    def lookup_position(self, key):
        # jit helper
        self = hint(self, promote=True)
        key = hint(key, promote=True)
        return _lookup_position_shared(self, key)

    def get_next_structure(self, key):
        # jit helper
        self = hint(self, promote=True)
        key = hint(key, promote=True)
        newstruct = _get_next_structure_shared(self, key)
        if not we_are_jitted():
            self._size_estimate -= self.size_estimate()
            self._size_estimate += newstruct.size_estimate()
        return newstruct

    def size_estimate(self):
        self = hint(self, promote=True)
        return _size_estimate(self)

@purefunction
def _lookup_position_shared(self, key):
    return self.keys.get(key, -1)

@purefunction
def _get_next_structure_shared(self, key):
    new_structure = self.other_structs.get(key)
    if new_structure is None:
        new_structure = self.new_structure(key)
    return new_structure

@purefunction
def _size_estimate(self):
    return self._size_estimate >> NUM_DIGITS


class State(object):
    def __init__(self, space):
        self.empty_structure = SharedStructure()
        self.emptylist = []


class SharedDictImplementation(W_DictMultiObject):

    def __init__(self, space):
        self.space = space
        self.structure = space.fromcache(State).empty_structure
        self.entries = space.fromcache(State).emptylist

    def impl_getitem(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.impl_getitem_str(space.str_w(w_lookup))
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().getitem(w_lookup)

    def impl_getitem_str(self, lookup):
        i = self.structure.lookup_position(lookup)
        if i == -1:
            return None
        return self.entries[i]

    def impl_setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            self._as_rdict().setitem(w_key, w_value)

    @unroll_safe
    def impl_setitem_str(self, key, w_value, shadows_type=True):
        i = self.structure.lookup_position(key)
        if i != -1:
            self.entries[i] = w_value
            return
        new_structure = self.structure.get_next_structure(key)
        if new_structure.length > len(self.entries):
            new_entries = [None] * new_structure.size_estimate()
            for i in range(len(self.entries)):
                new_entries[i] = self.entries[i]
            self.entries = new_entries

        self.entries[new_structure.length - 1] = w_value
        assert self.structure.length + 1 == new_structure.length
        self.structure = new_structure
            
    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            if (self.structure.last_key is not None and
                key == self.structure.last_key):
                self.entries[self.structure.length - 1] = None
                self.structure = self.structure.back_struct
                return
            self._as_rdict().delitem(w_key)
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().delitem(w_key)
        
    def impl_length(self):
        return self.structure.length

    def impl_iter(self):
        return SharedIteratorImplementation(self.space, self)

    def impl_keys(self):
        space = self.space
        return [space.wrap(key)
                    for (key, item) in self.structure.keys.iteritems()]

    def impl_values(self):
        return self.entries[:self.structure.length]

    def impl_items(self):
        space = self.space
        return [space.newtuple([space.wrap(key), self.entries[item]])
                    for (key, item) in self.structure.keys.iteritems()]
    def impl_clear(self):
        space = self.space
        self.structure = space.fromcache(State).empty_structure
        self.entries = space.fromcache(State).emptylist
    def _as_rdict(self):
        r_dict_content = self.initialize_as_rdict()
        for k, i in self.structure.keys.items():
            r_dict_content[self.space.wrap(k)] = self.entries[i]
        self._clear_fields()
        return self

    def _clear_fields(self):
        self.structure = None
        self.entries = None

class SharedIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.structure.keys.iteritems()

    def next_entry(self):
        implementation = self.dictimplementation
        assert isinstance(implementation, SharedDictImplementation)
        for key, index in self.iterator:
            w_value = implementation.entries[index]
            return self.space.wrap(key), w_value
        else:
            return None, None
