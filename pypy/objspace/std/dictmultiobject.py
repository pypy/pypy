import py
from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.module.__builtin__.__init__ import BUILTIN_TO_INDEX, OPTIMIZED_BUILTINS

from pypy.rlib.objectmodel import r_dict, we_are_translated

def _is_str(space, w_key):
    return space.is_w(space.type(w_key), space.w_str)

def _is_sane_hash(space, w_lookup_type):
    """ Handles the case of a non string key lookup.
    Types that have a sane hash/eq function should allow us to return True
    directly to signal that the key is not in the dict in any case.
    XXX The types should provide such a flag. """

    # XXX there are many more types
    return (space.is_w(w_lookup_type, space.w_NoneType) or
            space.is_w(w_lookup_type, space.w_int) or
            space.is_w(w_lookup_type, space.w_bool) or
            space.is_w(w_lookup_type, space.w_float)
            )


# DictImplementation lattice

# a dictionary starts with an EmptyDictImplementation, and moves down
# in this list:
#
#              EmptyDictImplementation
#                /                 \
#  SmallStrDictImplementation   SmallDictImplementation
#               |                   |
#   StrDictImplementation           |
#                \                 /
#               RDictImplementation
#
# (in addition, any dictionary can go back to EmptyDictImplementation)

class DictImplementation(object):
    
    def get(self, w_lookup):
        #return w_value or None
        raise NotImplementedError("abstract base class")

    def setitem_str(self,  w_key, w_value, shadows_type=True):
        #return implementation
        raise NotImplementedError("abstract base class")

    def setitem(self,  w_key, w_value):
        #return implementation
        raise NotImplementedError("abstract base class")

    def delitem(self, w_key):
        #return implementation
        raise NotImplementedError("abstract base class")
 
    def length(self):
        raise NotImplementedError("abstract base class")

    def iteritems(self):
        raise NotImplementedError("abstract base class")
    def iterkeys(self):
        raise NotImplementedError("abstract base class")
    def itervalues(self):
        raise NotImplementedError("abstract base class")


    def keys(self):
        iterator = self.iterkeys()
        result = []
        while 1:
            w_key = iterator.next()
            if w_key is not None:
                result.append(w_key)
            else:
                return result
    def values(self):
        iterator = self.itervalues()
        result = []
        while 1:
            w_value = iterator.next()
            if w_value is not None:
                result.append(w_value)
            else:
                return result
    def items(self):
        iterator = self.iteritems()
        result = []
        while 1:
            w_item = iterator.next()
            if w_item is not None:
                result.append(w_item)
            else:
                return result

#   the following method only makes sense when the option to use the
#   CALL_LIKELY_BUILTIN opcode is set. Otherwise it won't even be seen
#   by the annotator
    def get_builtin_indexed(self, i):
        w_key = self.space.wrap(OPTIMIZED_BUILTINS[i])
        return self.get(w_key)

# this method will only be seen whan a certain config option is used
    def shadows_anything(self):
        return True

    def set_shadows_anything(self):
        pass


# Iterator Implementation base classes

class IteratorImplementation(object):
    def __init__(self, space, implementation):
        self.space = space
        self.dictimplementation = implementation
        self.len = implementation.length()
        self.pos = 0

    def next(self):
        if self.dictimplementation is None:
            return None
        if self.len != self.dictimplementation.length():
            self.len = -1   # Make this error state sticky
            raise OperationError(self.space.w_RuntimeError,
                     self.space.wrap("dictionary changed size during iteration"))
        # look for the next entry
        w_result = self.next_entry()
        if w_result is not None:
            self.pos += 1
            return w_result
        # no more entries
        self.dictimplementation = None
        return None

    def next_entry(self):
        """ Purely abstract method
        """
        raise NotImplementedError

    def length(self):
        if self.dictimplementation is not None:
            return self.len - self.pos
        return 0



# concrete subclasses of the above

class EmptyDictImplementation(DictImplementation):
    def __init__(self, space):
        self.space = space

    def get(self, w_lookup):
        space = self.space
        if not _is_str(space, w_lookup) and not _is_sane_hash(space,
                                                        space.type(w_lookup)):
            # give hash a chance to raise an exception
            space.hash(w_lookup)
        return None

    def setitem(self, w_key, w_value):
        space = self.space
        if _is_str(space, w_key):
            if space.config.objspace.std.withsmalldicts:
                return SmallStrDictImplementation(space, w_key, w_value)
            else:
                return StrDictImplementation(space).setitem_str(w_key, w_value)
        else:
            if space.config.objspace.std.withsmalldicts:
                return SmallDictImplementation(space, w_key, w_value)
            else:
                return space.DefaultDictImpl(space).setitem(w_key, w_value)
    def setitem_str(self, w_key, w_value, shadows_type=True):
        return StrDictImplementation(self.space).setitem_str(w_key, w_value)
        #return SmallStrDictImplementation(self.space, w_key, w_value)

    def delitem(self, w_key):
        space = self.space
        if not _is_str(space, w_key) and not _is_sane_hash(space,
                                                           space.type(w_key)):
            # count hash
            space.hash(w_key)
        raise KeyError
    
    def length(self):
        return 0

    def iteritems(self):
        return EmptyIteratorImplementation(self.space, self)
    def iterkeys(self):
        return EmptyIteratorImplementation(self.space, self)
    def itervalues(self):
        return EmptyIteratorImplementation(self.space, self)

    def keys(self):
        return []
    def values(self):
        return []
    def items(self):
        return []


class EmptyIteratorImplementation(IteratorImplementation):
    def next_entry(self):
        return None

class Entry(object):
    def __init__(self):
        self.hash = 0
        self.w_key = None
        self.w_value = None
    def __repr__(self):
        return '<%r, %r, %r>'%(self.hash, self.w_key, self.w_value)

class SmallDictImplementation(DictImplementation):
    # XXX document the invariants here!
    
    def __init__(self, space, w_key, w_value):
        self.space = space
        self.entries = [Entry(), Entry(), Entry(), Entry(), Entry()]
        self.entries[0].hash = space.hash_w(w_key)
        self.entries[0].w_key = w_key
        self.entries[0].w_value = w_value
        self.valid = 1

    def _lookup(self, w_key):
        hash = self.space.hash_w(w_key)
        i = 0
        last = self.entries[self.valid]
        last.hash = hash
        last.w_key = w_key
        while 1:
            look_entry = self.entries[i]
            if look_entry.hash == hash and self.space.eq_w(look_entry.w_key, w_key):
                return look_entry
            i += 1

    def _convert_to_rdict(self):
        newimpl = self.space.DefaultDictImpl(self.space)
        i = 0
        while 1:
            entry = self.entries[i]
            if entry.w_value is None:
                break
            newimpl.setitem(entry.w_key, entry.w_value)
            i += 1
        return newimpl

    def setitem(self, w_key, w_value):
        entry = self._lookup(w_key)
        if entry.w_value is None:
            if self.valid == 4:
                return self._convert_to_rdict().setitem(w_key, w_value)
            self.valid += 1
        entry.w_value = w_value
        return self

    def setitem_str(self, w_key, w_value, shadows_type=True):
        return self.setitem(w_key, w_value)

    def delitem(self, w_key):
        entry = self._lookup(w_key)
        if entry.w_value is not None:
            for i in range(self.entries.index(entry), self.valid):
                self.entries[i] = self.entries[i+1]
            self.entries[self.valid] = entry
            entry.w_value = None
            self.valid -= 1
            if self.valid == 0:
                return self.space.emptydictimpl
            return self
        else:
            entry.w_key = None
            raise KeyError

    def length(self):
        return self.valid
    def get(self, w_lookup):
        entry = self._lookup(w_lookup)
        val = entry.w_value
        if val is None:
            entry.w_key = None
        return val

    def iteritems(self):
        return self._convert_to_rdict().iteritems()
    def iterkeys(self):
        return self._convert_to_rdict().iterkeys()
    def itervalues(self):
        return self._convert_to_rdict().itervalues()

    def keys(self):
        return [self.entries[i].w_key for i in range(self.valid)]
    def values(self):
        return [self.entries[i].w_value for i in range(self.valid)]
    def items(self):
        return [self.space.newtuple([e.w_key, e.w_value])
                    for e in [self.entries[i] for i in range(self.valid)]]


class StrEntry(object):
    def __init__(self):
        self.key = None
        self.w_value = None
    def __repr__(self):
        return '<%r, %r, %r>'%(self.hash, self.key, self.w_value)

class SmallStrDictImplementation(DictImplementation):
    # XXX document the invariants here!

    def __init__(self, space, w_key, w_value):
        self.space = space
        self.entries = [StrEntry(), StrEntry(), StrEntry(), StrEntry(), StrEntry()]
        key = space.str_w(w_key)
        self.entries[0].key = key
        self.entries[0].w_value = w_value
        self.valid = 1

    def _lookup(self, key):
        assert isinstance(key, str)
        _hash = hash(key)
        i = 0
        last = self.entries[self.valid]
        last.key = key
        while 1:
            look_entry = self.entries[i]
            if hash(look_entry.key) == _hash and look_entry.key == key:
                return look_entry
            i += 1

    def _convert_to_rdict(self):
        newimpl = self.space.DefaultDictImpl(self.space)
        i = 0
        while 1:
            entry = self.entries[i]
            if entry.w_value is None:
                break
            newimpl.setitem(self.space.wrap(entry.key), entry.w_value)
            i += 1
        return newimpl

    def _convert_to_sdict(self, w_value):
        # this relies on the fact that the new key is in the entries
        # list already.
        newimpl = StrDictImplementation(self.space)
        i = 0
        while 1:
            entry = self.entries[i]
            if entry.w_value is None:
                newimpl.content[entry.key] = w_value
                break
            newimpl.content[entry.key] = entry.w_value
            i += 1
        return newimpl

    def setitem(self, w_key, w_value):
        if not _is_str(self.space, w_key):
            return self._convert_to_rdict().setitem(w_key, w_value)
        return self.setitem_str(w_key, w_value)

    def setitem_str(self, w_key, w_value, shadows_type=True):
        entry = self._lookup(self.space.str_w(w_key))
        if entry.w_value is None:
            if self.valid == 4:
                return self._convert_to_sdict(w_value)
            self.valid += 1
        entry.w_value = w_value
        return self

    def delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            entry = self._lookup(space.str_w(w_key))
            if entry.w_value is not None:
                for i in range(self.entries.index(entry), self.valid):
                    self.entries[i] = self.entries[i+1]
                self.entries[self.valid] = entry
                entry.w_value = None
                self.valid -= 1
                if self.valid == 0:
                    return self.space.emptydictimpl
                return self
            else:
                entry.key = None
                raise KeyError
        elif _is_sane_hash(self.space, w_key_type):
            raise KeyError
        else:
            return self._convert_to_rdict().delitem(w_key)

    def length(self):
        return self.valid

    def get(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            entry = self._lookup(space.str_w(w_lookup))
            val = entry.w_value
            if val is None:
                entry.key = None
            return val
        elif _is_sane_hash(self.space, w_lookup_type):
            return None
        else:
            return self._convert_to_rdict().get(w_lookup)

    def iteritems(self):
        return self._convert_to_rdict().iteritems()
    def iterkeys(self):
        return self._convert_to_rdict().iterkeys()
    def itervalues(self):
        return self._convert_to_rdict().itervalues()

    def keys(self):
        return [self.space.wrap(self.entries[i].key) for i in range(self.valid)]
    def values(self):
        return [self.entries[i].w_value for i in range(self.valid)]
    def items(self):
        return [self.space.newtuple([self.space.wrap(e.key), e.w_value])
                    for e in [self.entries[i] for i in range(self.valid)]]


class StrDictImplementation(DictImplementation):
    def __init__(self, space):
        self.space = space
        self.content = {}
        
    def setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            return self.setitem_str(w_key, w_value)
        else:
            return self._as_rdict().setitem(w_key, w_value)

    def setitem_str(self, w_key, w_value, shadows_type=True):
        self.content[self.space.str_w(w_key)] = w_value
        return self

    def delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            del self.content[space.str_w(w_key)]
            if self.content:
                return self
            else:
                return space.emptydictimpl
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            return self._as_rdict().delitem(w_key)
        
    def length(self):
        return len(self.content)

    def get(self, w_lookup):
        space = self.space
        # -- This is called extremely often.  Hack for performance --
        if type(w_lookup) is space.StringObjectCls:
            return self.content.get(w_lookup.unwrap(space), None)
        # -- End of performance hack --
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.content.get(space.str_w(w_lookup), None)
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().get(w_lookup)

    def iteritems(self):
        return StrItemIteratorImplementation(self.space, self)

    def iterkeys(self):
        return StrKeyIteratorImplementation(self.space, self)

    def itervalues(self):
        return StrValueIteratorImplementation(self.space, self)

    def keys(self):
        space = self.space
        return [space.wrap(key) for key in self.content.iterkeys()]

    def values(self):
        return self.content.values()

    def items(self):
        space = self.space
        return [space.newtuple([space.wrap(key), w_value])
                    for (key, w_value) in self.content.iteritems()]


    def _as_rdict(self):
        newimpl = self.space.DefaultDictImpl(self.space)
        for k, w_v in self.content.items():
            newimpl.setitem(self.space.wrap(k), w_v)
        return newimpl

# the following are very close copies of the base classes above

class StrKeyIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.content.iterkeys()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for key in self.iterator:
            return self.space.wrap(key)
        else:
            return None

class StrValueIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.content.itervalues()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for w_value in self.iterator:
            return w_value
        else:
            return None

class StrItemIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.content.iteritems()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for key, w_value in self.iterator:
            return self.space.newtuple([self.space.wrap(key), w_value])
        else:
            return None


class ShadowDetectingDictImplementation(StrDictImplementation):
    def __init__(self, space, w_type):
        StrDictImplementation.__init__(self, space)
        self.w_type = w_type
        self.original_version_tag = w_type.version_tag
        if self.original_version_tag is None:
            self._shadows_anything = True
        else:
            self._shadows_anything = False

    def setitem_str(self, w_key, w_value, shadows_type=True):
        if shadows_type:
            self._shadows_anything = True
        return StrDictImplementation.setitem_str(
            self, w_key, w_value, shadows_type)

    def setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            if not self._shadows_anything:
                w_obj = self.w_type.lookup(space.str_w(w_key))
                if w_obj is not None:
                    self._shadows_anything = True
            return StrDictImplementation.setitem_str(
                self, w_key, w_value, False)
        else:
            return self._as_rdict().setitem(w_key, w_value)

    def shadows_anything(self):
        return (self._shadows_anything or 
                self.w_type.version_tag is not self.original_version_tag)

    def set_shadows_anything(self):
        self._shadows_anything = True

class WaryDictImplementation(StrDictImplementation):
    def __init__(self, space):
        StrDictImplementation.__init__(self, space)
        self.shadowed = [None] * len(BUILTIN_TO_INDEX)

    def setitem_str(self, w_key, w_value, shadows_type=True):
        key = self.space.str_w(w_key)
        i = BUILTIN_TO_INDEX.get(key, -1)
        if i != -1:
            self.shadowed[i] = w_value
        self.content[key] = w_value
        return self

    def delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            del self.content[key]
            i = BUILTIN_TO_INDEX.get(key, -1)
            if i != -1:
                self.shadowed[i] = None
            return self
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            return self._as_rdict().delitem(w_key)

    def get_builtin_indexed(self, i):
        return self.shadowed[i]

class RDictImplementation(DictImplementation):
    def __init__(self, space):
        self.space = space
        self.content = r_dict(space.eq_w, space.hash_w)

    def __repr__(self):
        return "%s<%s>" % (self.__class__.__name__, self.content)
        
    def setitem(self, w_key, w_value):
        self.content[w_key] = w_value
        return self

    def setitem_str(self, w_key, w_value, shadows_type=True):
        return self.setitem(w_key, w_value)

    def delitem(self, w_key):
        del self.content[w_key]
        if self.content:
            return self
        else:
            return self.space.emptydictimpl
        
    def length(self):
        return len(self.content)
    def get(self, w_lookup):
        return self.content.get(w_lookup, None)

    def iteritems(self):
        return RDictItemIteratorImplementation(self.space, self)
    def iterkeys(self):
        return RDictKeyIteratorImplementation(self.space, self)
    def itervalues(self):
        return RDictValueIteratorImplementation(self.space, self)

    def keys(self):
        return self.content.keys()
    def values(self):
        return self.content.values()
    def items(self):
        return [self.space.newtuple([w_key, w_val])
                    for w_key, w_val in self.content.iteritems()]


class RDictKeyIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.content.iterkeys()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for w_key in self.iterator:
            return w_key
        else:
            return None

class RDictValueIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.content.itervalues()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for w_value in self.iterator:
            return w_value
        else:
            return None

class RDictItemIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.content.iteritems()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for w_key, w_value in self.iterator:
            return self.space.newtuple([w_key, w_value])
        else:
            return None


class SharedStructure(object):
    def __init__(self, keys=None, length=0,
                 other_structs=None,
                 last_key=None,
                 back_struct=None):
        if keys is None:
            keys = {}
        self.keys = keys
        self.length = length
        self.back_struct = back_struct
        if other_structs is None:
            other_structs = []
        self.other_structs = other_structs
        self.last_key = last_key
        if last_key is not None:
            assert back_struct is not None
        self.propagating = False

    def new_structure(self, added_key):
        keys = {}
        for key, item in self.keys.iteritems():
            if item >= 0:
                keys[key] = item
        new_structure = SharedStructure(keys, self.length + 1,
                                        [], added_key, self)
        new_index = len(keys)
        new_structure.keys[added_key] = new_index
        self.keys[added_key] = ~len(self.other_structs)
        self.other_structs.append(new_structure)
        return new_structure


class State(object):
    def __init__(self, space):
        self.empty_structure = SharedStructure()
        self.empty_structure.propagating = True


class SharedDictImplementation(DictImplementation):

    def __init__(self, space):
        self.space = space
        self.structure = space.fromcache(State).empty_structure
        self.entries = []

    def get(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            lookup = space.str_w(w_lookup)
            i = self.structure.keys.get(lookup, -1)
            if i < 0:
                return None
            return self.entries[i]
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().get(w_lookup)

    def setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            return self.setitem_str(w_key, w_value)
        else:
            return self._as_rdict().setitem(w_key, w_value)

    def setitem_str(self, w_key, w_value, shadows_type=True):
        m = ~len(self.structure.other_structs)
        key = self.space.str_w(w_key)
        i = self.structure.keys.get(key, m)
        if i >= 0:
            self.entries[i] = w_value
            return self
        if not self.structure.propagating:
            return self._as_rdict(as_strdict=True).setitem_str(w_key, w_value)
        if i == m:
            new_structure = self.structure.new_structure(key)
        else:
            new_structure = self.structure.other_structs[~i]
            new_structure.propagating = True
        self.entries.append(w_value)
        assert self.structure.length + 1 == new_structure.length
        self.structure = new_structure
        assert self.structure.keys[key] >= 0
        return self
            
    def delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            if (self.structure.last_key is not None and
                key == self.structure.last_key):
                self.entries.pop()
                self.structure = self.structure.back_struct
                return self
            return self._as_rdict().delitem(w_key)
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            return self._as_rdict().delitem(w_key)
        
    def length(self):
        return self.structure.length

    def iteritems(self):
        return SharedItemIteratorImplementation(self.space, self)

    def iterkeys(self):
        return SharedKeyIteratorImplementation(self.space, self)

    def itervalues(self):
        return SharedValueIteratorImplementation(self.space, self)

    def keys(self):
        space = self.space
        return [space.wrap(key)
                    for (key, item) in self.structure.keys.iteritems()
                        if item >= 0]

    def values(self):
        return self.entries[:]

    def items(self):
        space = self.space
        return [space.newtuple([space.wrap(key), self.entries[item]])
                    for (key, item) in self.structure.keys.iteritems()
                        if item >= 0]

    def _as_rdict(self, as_strdict=False):
        if as_strdict:
            newimpl = StrDictImplementation(self.space)
        else:
            newimpl = self.space.DefaultDictImpl(self.space)
        for k, i in self.structure.keys.items():
            if i >= 0:
                newimpl.setitem_str(self.space.wrap(k), self.entries[i])
        return newimpl


class SharedValueIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.values = dictimplementation.entries

    def next(self):
        if self.pos < self.len:
            return self.values[self.pos]
        else:
            self.values = None
            return None

class SharedItemIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.structure.keys.iteritems()

    def next_entry(self):
        implementation = self.dictimplementation
        assert isinstance(implementation, SharedDictImplementation)
        for key, index in self.iterator:
            if index >= 0:
                w_value = implementation.entries[index]
                return self.space.newtuple([self.space.wrap(key), w_value])
        else:
            return None

class SharedKeyIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.structure.keys.iteritems()

    def next_entry(self):
        implementation = self.dictimplementation
        assert isinstance(implementation, SharedDictImplementation)
        for key, index in self.iterator:
            if index >= 0:
                return self.space.wrap(key)
        else:
            return None


import time, py

class DictInfo(object):
    _dict_infos = []
    def __init__(self):
        self.id = len(self._dict_infos)

        self.setitem_strs = 0; self.setitems = 0;  self.delitems = 0
        self.lengths = 0;   self.gets = 0
        self.iteritems = 0; self.iterkeys = 0; self.itervalues = 0
        self.keys = 0;      self.values = 0;   self.items = 0

        self.maxcontents = 0

        self.reads = 0
        self.hits = self.misses = 0
        self.writes = 0
        self.iterations = 0
        self.listings = 0

        self.seen_non_string_in_write = 0
        self.seen_non_string_in_read_first = 0
        self.size_on_non_string_seen_in_read = -1
        self.size_on_non_string_seen_in_write = -1

        self.createtime = time.time()
        self.lifetime = -1.0

        if not we_are_translated():
            # very probable stack from here:
            # 0 - us
            # 1 - MeasuringDictImplementation.__init__
            # 2 - W_DictMultiObject.__init__
            # 3 - space.newdict
            # 4 - newdict's caller.  let's look at that
            try:
                frame = sys._getframe(4)
            except ValueError:
                pass # might be at import time
            else:
                self.sig = '(%s:%s)%s'%(frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)

        self._dict_infos.append(self)
    def __repr__(self):
        args = []
        for k in py.builtin.sorted(self.__dict__):
            v = self.__dict__[k]
            if v != 0:
                args.append('%s=%r'%(k, v))
        return '<DictInfo %s>'%(', '.join(args),)

class OnTheWayOut:
    def __init__(self, info):
        self.info = info
    def __del__(self):
        self.info.lifetime = time.time() - self.info.createtime

class MeasuringDictImplementation(DictImplementation):
    def __init__(self, space):
        self.space = space
        self.content = r_dict(space.eq_w, space.hash_w)
        self.info = DictInfo()
        self.thing_with_del = OnTheWayOut(self.info)

    def __repr__(self):
        return "%s<%s>" % (self.__class__.__name__, self.content)

    def _is_str(self, w_key):
        space = self.space
        return space.is_true(space.isinstance(w_key, space.w_str))
    def _read(self, w_key):
        self.info.reads += 1
        if not self.info.seen_non_string_in_write \
               and not self.info.seen_non_string_in_read_first \
               and not self._is_str(w_key):
            self.info.seen_non_string_in_read_first = True
            self.info.size_on_non_string_seen_in_read = len(self.content)
        hit = w_key in self.content
        if hit:
            self.info.hits += 1
        else:
            self.info.misses += 1

    def setitem(self, w_key, w_value):
        if not self.info.seen_non_string_in_write and not self._is_str(w_key):
            self.info.seen_non_string_in_write = True
            self.info.size_on_non_string_seen_in_write = len(self.content)
        self.info.setitems += 1
        self.info.writes += 1
        self.content[w_key] = w_value
        self.info.maxcontents = max(self.info.maxcontents, len(self.content))
        return self
    def setitem_str(self, w_key, w_value, shadows_type=True):
        self.info.setitem_strs += 1
        return self.setitem(w_key, w_value)
    def delitem(self, w_key):
        if not self.info.seen_non_string_in_write \
               and not self.info.seen_non_string_in_read_first \
               and not self._is_str(w_key):
            self.info.seen_non_string_in_read_first = True
            self.info.size_on_non_string_seen_in_read = len(self.content)
        self.info.delitems += 1
        self.info.writes += 1
        del self.content[w_key]
        return self

    def length(self):
        self.info.lengths += 1
        return len(self.content)
    def get(self, w_lookup):
        self.info.gets += 1
        self._read(w_lookup)
        return self.content.get(w_lookup, None)

    def iteritems(self):
        self.info.iteritems += 1
        self.info.iterations += 1
        return RDictItemIteratorImplementation(self.space, self)
    def iterkeys(self):
        self.info.iterkeys += 1
        self.info.iterations += 1
        return RDictKeyIteratorImplementation(self.space, self)
    def itervalues(self):
        self.info.itervalues += 1
        self.info.iterations += 1
        return RDictValueIteratorImplementation(self.space, self)

    def keys(self):
        self.info.keys += 1
        self.info.listings += 1
        return self.content.keys()
    def values(self):
        self.info.values += 1
        self.info.listings += 1
        return self.content.values()
    def items(self):
        self.info.items += 1
        self.info.listings += 1
        return [self.space.newtuple([w_key, w_val])
                    for w_key, w_val in self.content.iteritems()]


_example = DictInfo()
del DictInfo._dict_infos[-1]
tmpl = 'os.write(fd, "%(attr)s" + ": " + str(info.%(attr)s) + "\\n")'
bodySrc = []
for attr in py.builtin.sorted(_example.__dict__):
    if attr == 'sig':
        continue
    bodySrc.append(tmpl%locals())
exec py.code.Source('''
from pypy.rlib.objectmodel import current_object_addr_as_int
def _report_one(fd, info):
    os.write(fd, "_address" + ": " + str(current_object_addr_as_int(info))
                 + "\\n")
    %s
'''%'\n    '.join(bodySrc)).compile()

def report():
    if not DictInfo._dict_infos:
        return
    os.write(2, "Starting multidict report.\n")
    fd = os.open('dictinfo.txt', os.O_CREAT|os.O_WRONLY|os.O_TRUNC, 0644)
    for info in DictInfo._dict_infos:
        os.write(fd, '------------------\n')
        _report_one(fd, info)
    os.close(fd)
    os.write(2, "Reporting done.\n")

class W_DictMultiObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    def __init__(w_self, space, wary=False, sharing=False):
        if space.config.objspace.opcodes.CALL_LIKELY_BUILTIN and wary:
            w_self.implementation = WaryDictImplementation(space)
        elif space.config.objspace.std.withdictmeasurement:
            w_self.implementation = MeasuringDictImplementation(space)
        elif space.config.objspace.std.withsharingdict and sharing:
            w_self.implementation = SharedDictImplementation(space)
        else:
            w_self.implementation = space.emptydictimpl

    def initialize_content(w_self, list_pairs_w):
        impl = w_self.implementation
        for w_k, w_v in list_pairs_w:
            impl = impl.setitem(w_k, w_v)
        w_self.implementation = impl

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.implementation)

    def unwrap(w_dict, space):
        result = {}
        items = w_dict.implementation.items()
        for w_pair in items:
            key, val = space.unwrap(w_pair)
            result[key] = val
        return result

    def missing_method(w_dict, space, w_key):
        if not space.is_w(space.type(w_dict), space.w_dict):
            w_missing = space.lookup(w_dict, "__missing__")
            if w_missing is None:
                return None
            return space.call_function(w_missing, w_dict, w_key)
        else:
            return None

    def len(w_self):
        return w_self.implementation.length()

    def get(w_dict, w_key, w_default):
        w_value = w_dict.implementation.get(w_key)
        if w_value is not None:
            return w_value
        else:
            return w_default

    def set_str_keyed_item(w_dict, w_key, w_value, shadows_type=True):
        w_dict.implementation = w_dict.implementation.setitem_str(
            w_key, w_value, shadows_type)

registerimplementation(W_DictMultiObject)


def init__DictMulti(space, w_dict, __args__):
    w_src, w_kwds = __args__.parse('dict',
                          (['seq_or_map'], None, 'kwargs'), # signature
                          [W_DictMultiObject(space)])            # default argument
    # w_dict.implementation = space.emptydictimpl
    #                              ^^^ disabled only for CPython compatibility
    if space.findattr(w_src, space.wrap("keys")) is None:
        list_of_w_pairs = space.unpackiterable(w_src)
        for w_pair in list_of_w_pairs:
            pair = space.unpackiterable(w_pair)
            if len(pair)!=2:
                raise OperationError(space.w_ValueError,
                             space.wrap("dict() takes a sequence of pairs"))
            w_k, w_v = pair
            w_dict.implementation = w_dict.implementation.setitem(w_k, w_v)
    else:
        if space.is_true(w_src):
            from pypy.objspace.std.dicttype import update1
            update1(space, w_dict, w_src)
    if space.is_true(w_kwds):
        from pypy.objspace.std.dicttype import update1
        update1(space, w_dict, w_kwds)

def getitem__DictMulti_ANY(space, w_dict, w_lookup):
    w_value = w_dict.implementation.get(w_lookup)
    if w_value is not None:
        return w_value

    w_missing_item = w_dict.missing_method(space, w_lookup)
    if w_missing_item is not None:
        return w_missing_item

    raise OperationError(space.w_KeyError, w_lookup)

def setitem__DictMulti_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    w_dict.implementation = w_dict.implementation.setitem(w_newkey, w_newvalue)

def delitem__DictMulti_ANY(space, w_dict, w_lookup):
    try:
        w_dict.implementation = w_dict.implementation.delitem(w_lookup)
    except KeyError:
        raise OperationError(space.w_KeyError, w_lookup)
    
def len__DictMulti(space, w_dict):
    return space.wrap(w_dict.implementation.length())

def contains__DictMulti_ANY(space, w_dict, w_lookup):
    return space.newbool(w_dict.implementation.get(w_lookup) is not None)

dict_has_key__DictMulti_ANY = contains__DictMulti_ANY

def iter__DictMulti(space, w_dict):
    return W_DictMultiIterObject(space, w_dict.implementation.iterkeys())

def eq__DictMulti_DictMulti(space, w_left, w_right):
    if space.is_w(w_left, w_right):
        return space.w_True

    if w_left.implementation.length() != w_right.implementation.length():
        return space.w_False
    iteratorimplementation = w_left.implementation.iteritems()
    while 1:
        w_item = iteratorimplementation.next()
        if w_item is None:
            break
        w_key = space.getitem(w_item, space.wrap(0))
        w_val = space.getitem(w_item, space.wrap(1))
        w_rightval = w_right.implementation.get(w_key)
        if w_rightval is None:
            return space.w_False
        if not space.eq_w(w_val, w_rightval):
            return space.w_False
    return space.w_True

def characterize(space, aimpl, bimpl):
    """ (similar to CPython) 
    returns the smallest key in acontent for which b's value is different or absent and this value """
    w_smallest_diff_a_key = None
    w_its_value = None
    iteratorimplementation = aimpl.iteritems()
    while 1:
        w_item = iteratorimplementation.next()
        if w_item is None:
            break
        w_key = space.getitem(w_item, space.wrap(0))
        w_val = space.getitem(w_item, space.wrap(1))
        if w_smallest_diff_a_key is None or space.is_true(space.lt(w_key, w_smallest_diff_a_key)):
            w_bvalue = bimpl.get(w_key)
            if w_bvalue is None:
                w_its_value = w_val
                w_smallest_diff_a_key = w_key
            else:
                if not space.eq_w(w_val, w_bvalue):
                    w_its_value = w_val
                    w_smallest_diff_a_key = w_key
    return w_smallest_diff_a_key, w_its_value

def lt__DictMulti_DictMulti(space, w_left, w_right):
    # Different sizes, no problem
    leftimpl = w_left.implementation
    rightimpl = w_right.implementation
    if leftimpl.length() < rightimpl.length():
        return space.w_True
    if leftimpl.length() > rightimpl.length():
        return space.w_False

    # Same size
    w_leftdiff, w_leftval = characterize(space, leftimpl, rightimpl)
    if w_leftdiff is None:
        return space.w_False
    w_rightdiff, w_rightval = characterize(space, rightimpl, leftimpl)
    if w_rightdiff is None:
        # w_leftdiff is not None, w_rightdiff is None
        return space.w_True 
    w_res = space.lt(w_leftdiff, w_rightdiff)
    if (not space.is_true(w_res) and
        space.eq_w(w_leftdiff, w_rightdiff) and 
        w_rightval is not None):
        w_res = space.lt(w_leftval, w_rightval)
    return w_res

def dict_copy__DictMulti(space, w_self):
    from pypy.objspace.std.dicttype import update1
    w_new = W_DictMultiObject(space)
    update1(space, w_new, w_self)
    return w_new

def dict_items__DictMulti(space, w_self):
    return space.newlist(w_self.implementation.items())

def dict_keys__DictMulti(space, w_self):
    return space.newlist(w_self.implementation.keys())

def dict_values__DictMulti(space, w_self):
    return space.newlist(w_self.implementation.values())

def dict_iteritems__DictMulti(space, w_self):
    return W_DictMultiIterObject(space, w_self.implementation.iteritems())

def dict_iterkeys__DictMulti(space, w_self):
    return W_DictMultiIterObject(space, w_self.implementation.iterkeys())

def dict_itervalues__DictMulti(space, w_self):
    return W_DictMultiIterObject(space, w_self.implementation.itervalues())

def dict_clear__DictMulti(space, w_self):
    w_self.implementation = space.emptydictimpl

def dict_get__DictMulti_ANY_ANY(space, w_dict, w_lookup, w_default):
    return w_dict.get(w_lookup, w_default)

def dict_pop__DictMulti_ANY(space, w_dict, w_key, w_defaults):
    defaults = space.unpackiterable(w_defaults)
    len_defaults = len(defaults)
    if len_defaults > 1:
        raise OperationError(space.w_TypeError, space.wrap("pop expected at most 2 arguments, got %d" % (1 + len_defaults, )))
    w_item = w_dict.implementation.get(w_key)
    if w_item is None:
        if len_defaults > 0:
            return defaults[0]
        else:
            raise OperationError(space.w_KeyError, w_key)
    else:
        w_dict.implementation.delitem(w_key)
        return w_item


from pypy.objspace.std.dictobject import dictrepr

def repr__DictMulti(space, w_dict):
    if w_dict.implementation.length() == 0:
        return space.wrap('{}')
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return dictrepr(space, w_currently_in_repr, w_dict)


# ____________________________________________________________
# Iteration


class W_DictMultiIterObject(W_Object):
    from pypy.objspace.std.dicttype import dictiter_typedef as typedef

    def __init__(w_self, space, iteratorimplementation):
        w_self.space = space
        w_self.iteratorimplementation = iteratorimplementation

registerimplementation(W_DictMultiIterObject)

def iter__DictMultiIterObject(space, w_dictiter):
    return w_dictiter

def next__DictMultiIterObject(space, w_dictiter):
    iteratorimplementation = w_dictiter.iteratorimplementation
    w_result = iteratorimplementation.next()
    if w_result is not None:
        return w_result
    raise OperationError(space.w_StopIteration, space.w_None)

def len__DictMultiIterObject(space, w_dictiter):
    iteratorimplementation = w_dictiter.iteratorimplementation
    return space.wrap(iteratorimplementation.length())

# ____________________________________________________________

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
