from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway

from pypy.rpython.objectmodel import r_dict, we_are_translated

def _is_str(space, w_key):
    return space.is_w(space.type(w_key), space.w_str)

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
    
##     def get(self, w_lookup):
##         return w_value or None
##     def setitem_str(self,  w_key, w_value):
##         return implementation
##     def setitem(self,  w_key, w_value):
##         return implementation
##     def delitem(self, w_key):
##         return implementation
    
##     def length(self):
##         pass

##     def iteritems(self):
##         pass
##     def iterkeys(self):
##         pass
##     def itervalues(self):
##         pass

    def keys(self):
        return [w_k for w_k in self.iterkeys()]
    def values(self):
        return [w_v for w_v in self.itervalues()]
    def items(self):
        return [(w_key, w_value) or w_key, w_value in self.iteritems()]

class EmptyDictImplementation(DictImplementation):
    def __init__(self, space):
        self.space = space

    def get(self, w_lookup):
        return None
    def setitem(self, w_key, w_value):
        if _is_str(self.space, w_key):
            return StrDictImplementation(self.space).setitem_str(w_key, w_value)
            #return SmallStrDictImplementation(self.space, w_key, w_value)
        else:
            return RDictImplementation(self.space).setitem(w_key, w_value)
        #return SmallDictImplementation(self.space, w_key, w_value)
    def setitem_str(self, w_key, w_value):
        return StrDictImplementation(self.space).setitem_str(w_key, w_value)
        #return SmallStrDictImplementation(self.space, w_key, w_value)
    def delitem(self, w_key):
        raise KeyError
    
    def length(self):
        return 0

    def iteritems(self):
        return RDictImplementation(self.space).iteritems()
    def iterkeys(self):
        return RDictImplementation(self.space).iterkeys()
    def itervalues(self):
        return RDictImplementation(self.space).itervalues()

    def keys(self):
        return []
    def values(self):
        return []
    def items(self):
        return []

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
        newimpl = RDictImplementation(self.space)
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

    setitem_str = setitem

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
            raise KeyError        
    
    def length(self):
        return self.valid
    def get(self, w_lookup):
        return self._lookup(w_lookup).w_value

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
        return [(e.w_key, e.w_value) for e in [self.entries[i] for i in range(self.valid)]]

class StrEntry(object):
    def __init__(self):
        self.hash = 0
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
        self.entries[0].hash = hash(key)
        self.entries[0].key = key
        self.entries[0].w_value = w_value
        self.valid = 1

    def _is_sane_hash(self, w_lookup_type):
        """ Handles the case of a non string key lookup.
        Types that have a sane hash/eq function should allow us to return True
        directly to signal that the key is not in the dict in any case.
        XXX The types should provide such a flag. """
    
        space = self.space
        # XXX there are many more such types
        return space.is_w(w_lookup_type, space.w_NoneType) or space.is_w(w_lookup_type, space.w_int)

    def _lookup(self, key):
        assert isinstance(key, str)
        _hash = hash(key)
        i = 0
        last = self.entries[self.valid]
        last.hash = _hash
        last.key = key
        while 1:
            look_entry = self.entries[i]
            if look_entry.hash == _hash and look_entry.key == key:
                return look_entry
            i += 1

    def _convert_to_rdict(self):
        newimpl = RDictImplementation(self.space)
        i = 0
        while 1:
            entry = self.entries[i]
            if entry.w_value is None:
                break
            newimpl.content[self.space.wrap(entry.key)] = entry.w_value
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
    
    def setitem_str(self, w_key, w_value):
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
                raise KeyError
        elif self._is_sane_hash(w_key_type):
            raise KeyError
        else:
            return self._convert_to_rdict().delitem(w_key)
        
    def length(self):
        return self.valid
    
    def get(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self._lookup(space.str_w(w_lookup)).w_value
        elif self._is_sane_hash(w_lookup_type):
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
        return [(self.space.wrap(e.key), e.w_value)
                for e in [self.entries[i] for i in range(self.valid)]]

class StrDictImplementation(DictImplementation):
    def __init__(self, space):
        self.space = space
        self.content = {}
        
    def setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.content[space.str_w(w_key)] = w_value
            return self
        else:
            return self._as_rdict().setitem(w_key, w_value)

    def setitem_str(self, w_key, w_value):
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
        elif self._is_sane_hash(w_key_type):
            raise KeyError
        else:
            return self._as_rdict().delitem(w_key)
        
    def length(self):
        return len(self.content)

    def get(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.content.get(space.str_w(w_lookup), None)
        elif self._is_sane_hash(w_lookup_type):
            return None
        else:
            return self._as_rdict().get(w_lookup)

    def iteritems(self):
        return self._as_rdict().iteritems()

    def iterkeys(self):
        return self._as_rdict().iterkeys()

    def itervalues(self):
        return self._as_rdict().itervalues()

    def keys(self):
        space = self.space
        return [space.wrap(key) for key in self.content.iterkeys()]

    def values(self):
        return self.content.values()

    def items(self):
        space = self.space
        return [(space.wrap(key), w_value) for (key, w_value) in self.content.iteritems()]

    def _is_sane_hash(self, w_lookup_type):
        """ Handles the case of a non string key lookup.
        Types that have a sane hash/eq function should allow us to return True
        directly to signal that the key is not in the dict in any case.
        XXX The types should provide such a flag. """
    
        space = self.space
        # XXX there are much more types
        return space.is_w(w_lookup_type, space.w_NoneType) or space.is_w(w_lookup_type, space.w_int)

    def _as_rdict(self):
        newimpl = RDictImplementation(self.space)
        for k, w_v in self.content.items():
            newimpl.setitem(self.space.wrap(k), w_v)
        return newimpl

class RDictImplementation(DictImplementation):
    def __init__(self, space):
        self.space = space
        self.content = r_dict(space.eq_w, space.hash_w)

    def __repr__(self):
        return "%s<%s>" % (self.__class__.__name__, self.content)
        
    def setitem(self, w_key, w_value):
        self.content[w_key] = w_value
        return self
    setitem_str = setitem
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
        return self.content.iteritems()
    def iterkeys(self):
        return self.content.iterkeys()
    def itervalues(self):
        return self.content.itervalues()

    def keys(self):
        return self.content.keys()
    def values(self):
        return self.content.values()
    def items(self):
        return self.content.items()

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
        for k in sorted(self.__dict__):
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
    def setitem_str(self, w_key, w_value):
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
        return self.content.iteritems()
    def iterkeys(self):
        self.info.iterkeys += 1
        self.info.iterations += 1
        return self.content.iterkeys()
    def itervalues(self):
        self.info.itervalues += 1
        self.info.iterations += 1
        return self.content.itervalues()

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
        return self.content.items()

_example = DictInfo()
del DictInfo._dict_infos[-1]
tmpl = 'os.write(fd, "%(attr)s" + ": " + str(info.%(attr)s) + "\\n")'
bodySrc = []
for attr in sorted(_example.__dict__):
    if attr == 'sig':
        continue
    bodySrc.append(tmpl%locals())
exec py.code.Source('''
def _report_one(fd, info):
    os.write(fd, "_address" + ": " + str(id(info)) + "\\n")
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

    def __init__(w_self, space):
        if space.config.objspace.std.withdictmeasurement:
            w_self.implementation = MeasuringDictImplementation(space)
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
        for w_key, w_value in w_dict.implementation.iteritems():
            # generic mixed types unwrap
            result[space.unwrap(w_key)] = space.unwrap(w_value)
        return result

    def len(w_self):
        return w_self.implementation.length()

    def get(w_dict, w_key, w_default):
        w_value = w_dict.implementation.get(w_key)
        if w_value is not None:
            return w_value
        else:
            return w_default

    def set_str_keyed_item(w_dict, w_key, w_value):
        w_dict.implementation = w_dict.implementation.setitem_str(w_key, w_value)

registerimplementation(W_DictMultiObject)


def init__DictMulti(space, w_dict, __args__):
    w_src, w_kwds = __args__.parse('dict',
                          (['seq_or_map'], None, 'kwargs'), # signature
                          [W_DictMultiObject(space)])            # default argument
    # w_dict.implementation = space.emptydictimpl
    #                              ^^^ disabled only for CPython compatibility
    try:
        space.getattr(w_src, space.wrap("keys"))
    except OperationError:
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
    return W_DictMultiIter_Keys(space, w_dict.implementation)

def eq__DictMulti_DictMulti(space, w_left, w_right):
    if space.is_w(w_left, w_right):
        return space.w_True

    if w_left.implementation.length() != w_right.implementation.length():
        return space.w_False
    for w_key, w_val in w_left.implementation.iteritems():
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
    for w_key, w_val in aimpl.iteritems():
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
    return space.newlist([space.newtuple([w_k, w_v]) for w_k, w_v in w_self.implementation.iteritems()])

def dict_keys__DictMulti(space, w_self):
    return space.newlist(w_self.implementation.keys())

def dict_values__DictMulti(space, w_self):
    return space.newlist(w_self.implementation.values())

def dict_iteritems__DictMulti(space, w_self):
    return W_DictMultiIter_Items(space, w_self.implementation)

def dict_iterkeys__DictMulti(space, w_self):
    return W_DictMultiIter_Keys(space, w_self.implementation)

def dict_itervalues__DictMulti(space, w_self):
    return W_DictMultiIter_Values(space, w_self.implementation)

def dict_clear__DictMulti(space, w_self):
    w_self.implementation = space.emptydictimpl

def dict_get__DictMulti_ANY_ANY(space, w_dict, w_lookup, w_default):
    return w_dict.get(w_lookup, w_default)

app = gateway.applevel('''
    def dictrepr(currently_in_repr, d):
        # Now we only handle one implementation of dicts, this one.
        # The fix is to move this to dicttype.py, and do a
        # multimethod lookup mapping str to StdObjSpace.str
        # This cannot happen until multimethods are fixed. See dicttype.py
            dict_id = id(d)
            if dict_id in currently_in_repr:
                return '{...}'
            currently_in_repr[dict_id] = 1
            try:
                items = []
                # XXX for now, we cannot use iteritems() at app-level because
                #     we want a reasonable result instead of a RuntimeError
                #     even if the dict is mutated by the repr() in the loop.
                for k, v in d.items():
                    items.append(repr(k) + ": " + repr(v))
                return "{" +  ', '.join(items) + "}"
            finally:
                try:
                    del currently_in_repr[dict_id]
                except:
                    pass
''', filename=__file__)

dictrepr = app.interphook("dictrepr")

def repr__DictMulti(space, w_dict):
    if w_dict.implementation.length() == 0:
        return space.wrap('{}')
    w_currently_in_repr = space.getexecutioncontext()._py_repr
    return dictrepr(space, w_currently_in_repr, w_dict)


# ____________________________________________________________
# Iteration

class W_DictMultiIterObject(W_Object):
    from pypy.objspace.std.dicttype import dictiter_typedef as typedef

    def __init__(w_self, space, implementation):
        w_self.space = space
        w_self.implementation = implementation
        w_self.len = implementation.length()
        w_self.pos = 0
        w_self.setup_iterator()


registerimplementation(W_DictMultiIterObject)

class W_DictMultiIter_Keys(W_DictMultiIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.implementation.iterkeys()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_key in w_self.iterator:
            return w_key
        else:
            return None

class W_DictMultiIter_Values(W_DictMultiIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.implementation.itervalues()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_value in w_self.iterator:
            return w_value
        else:
            return None

class W_DictMultiIter_Items(W_DictMultiIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.implementation.iteritems()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_key, w_value in w_self.iterator:
            return w_self.space.newtuple([w_key, w_value])
        else:
            return None


def iter__DictMultiIterObject(space, w_dictiter):
    return w_dictiter

def next__DictMultiIterObject(space, w_dictiter):
    implementation = w_dictiter.implementation
    if implementation is not None:
        if w_dictiter.len != implementation.length():
            w_dictiter.len = -1   # Make this error state sticky
            raise OperationError(space.w_RuntimeError,
                     space.wrap("dictionary changed size during iteration"))
        # look for the next entry
        w_result = w_dictiter.next_entry()
        if w_result is not None:
            w_dictiter.pos += 1
            return w_result
        # no more entries
        w_dictiter.implementation = None
    raise OperationError(space.w_StopIteration, space.w_None)

def len__DictMultiIterObject(space, w_dictiter):
    implementation = w_dictiter.implementation
    if implementation is None or w_dictiter.len == -1:
        return space.wrap(0)
    return space.wrap(w_dictiter.len - w_dictiter.pos)

# ____________________________________________________________

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
