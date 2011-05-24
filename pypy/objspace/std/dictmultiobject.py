import py, sys
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.interpreter import gateway
from pypy.interpreter.argument import Signature
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.module.__builtin__.__init__ import BUILTIN_TO_INDEX, OPTIMIZED_BUILTINS

from pypy.rlib.objectmodel import r_dict, we_are_translated
from pypy.objspace.std.settype import set_typedef as settypedef

from pypy.rlib import rerased

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

class W_DictMultiObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    @staticmethod
    def allocate_and_init_instance(space, w_type=None, module=False,
                                   instance=False, classofinstance=None,
                                   strdict=False):

        if space.config.objspace.std.withcelldict and module:
            from pypy.objspace.std.celldict import ModuleDictStrategy
            assert w_type is None
            strategy = space.fromcache(ModuleDictStrategy)
            storage = strategy.get_empty_storage()

        elif space.config.objspace.opcodes.CALL_LIKELY_BUILTIN and module:
            assert w_type is None
            # create new Strategy everytime, because each must have its own shadow-attribute
            strategy = WaryDictStrategy(space)

        elif space.config.objspace.std.withdictmeasurement:
            assert w_type is None
            strategy = space.fromcache(MeasuringDictStrategy)

        elif instance or strdict or module:
            assert w_type is None
            strategy = space.fromcache(StringDictStrategy)

        else:
            strategy = space.fromcache(EmptyDictStrategy)

        if w_type is None:
            w_type = space.w_dict
        storage = strategy.get_empty_storage()
        w_self = space.allocate_instance(W_DictMultiObject, w_type)
        W_DictMultiObject.__init__(w_self, space, strategy, storage)
        return w_self

    def __init__(self, space, strategy, storage):
        self.space = space
        self.strategy = strategy
        self.dstorage = storage

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.strategy)

    def unwrap(w_dict, space):
        result = {}
        items = w_dict.items()
        for w_pair in items:
            key, val = space.unwrap(w_pair)
            result[key] = val
        return result

    def missing_method(w_dict, space, w_key):
        if not space.is_w(space.type(w_dict), space.w_dict):
            w_missing = space.lookup(w_dict, "__missing__")
            if w_missing is None:
                return None
            return space.get_and_call_function(w_missing, w_dict, w_key)
        else:
            return None

    def initialize_content(w_self, list_pairs_w):
        for w_k, w_v in list_pairs_w:
            w_self.setitem(w_k, w_v)

def _add_indirections():
    dict_methods = "setitem setitem_str getitem \
                    getitem_str delitem length \
                    clear keys values \
                    items iter setdefault \
                    popitem get_builtin_indexed".split()

    def make_method(method):
        def f(self, *args):
            return getattr(self.strategy, method)(self, *args)
        f.func_name = method
        return f

    for method in dict_methods:
        setattr(W_DictMultiObject, method, make_method(method))

_add_indirections()

class DictStrategy(object):

    def __init__(self, space):
        self.space = space

    def get_empty_storage(self):
        raise NotImplementedError

    def initialize_as_rdict(self):
        assert self.r_dict_content is None
        self.r_dict_content = r_dict(self.space.eq_w, self.space.hash_w)
        return self.r_dict_content

    def keys(self, w_dict):
        iterator = self.iter(w_dict)
        result = []
        while 1:
            w_key, w_value = iterator.next()
            if w_key is not None:
                result.append(w_key)
            else:
                return result

    def values(self, w_dict):
        iterator = self.iter(w_dict)
        result = []
        while 1:
            w_key, w_value = iterator.next()
            if w_value is not None:
                result.append(w_value)
            else:
                return result

    def items(self, w_dict):
        iterator = self.iter(w_dict)
        result = []
        while 1:
            w_key, w_value = iterator.next()
            if w_key is not None:
                result.append(self.space.newtuple([w_key, w_value]))
            else:
                return result

    def get_builtin_indexed(self, w_dict, i):
        key = OPTIMIZED_BUILTINS[i]
        return self.getitem_str(w_dict, key)

    def clear(self, w_dict):
        strategy = self.space.fromcache(EmptyDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.strategy = strategy
        w_dict.dstorage = storage

    # _________________________________________________________________
    # implementation methods

class EmptyDictStrategy(DictStrategy):

    cast_to_void_star, cast_from_void_star = rerased.new_erasing_pair("empty")
    cast_to_void_star = staticmethod(cast_to_void_star)
    cast_from_void_star = staticmethod(cast_from_void_star)

    def __init__(self, space):
        self.space = space

    def get_empty_storage(self):
       return self.cast_to_void_star(None)

    def switch_to_correct_strategy(self, w_dict, w_key):
        #XXX implement other strategies later
        if type(w_key) is self.space.StringObjectCls:
            self.switch_to_string_strategy(w_dict)
            return

        strategy = self.space.fromcache(ObjectDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.strategy = strategy
        w_dict.dstorage = storage

    def switch_to_string_strategy(self, w_dict):
        strategy = self.space.fromcache(StringDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.strategy = strategy
        w_dict.dstorage = storage

    def getitem(self, w_dict, w_key):
        #return w_value or None
        # in case the key is unhashable, try to hash it
        self.space.hash(w_key)
        # return None anyway
        return None

    def getitem_str(self, w_dict, key):
        #return w_value or None
        return None

    def setdefault(self, w_dict, w_key, w_default):
        # here the dict is always empty
        self.switch_to_correct_strategy(w_dict, w_key)
        w_dict.setitem(w_key, w_default)
        return w_default

    def setitem(self, w_dict, w_key, w_value):
        self.switch_to_correct_strategy(w_dict, w_key)
        w_dict.setitem(w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        self.switch_to_string_strategy(w_dict)
        self.setitem_str(w_dict, key, w_value)

    def delitem(self, w_dict, w_key):
        # in case the key is unhashable, try to hash it
        self.space.hash(w_key)
        raise KeyError

    def length(self, w_dict):
        return 0

    def iter(self, w_dict):
        return EmptyIteratorImplementation()

    def impl_clear(self, w_dict):
        self.r_dict_content = None

    def clear(self, w_dict):
        return

    def _as_rdict(self):
        r_dict_content = self.initialize_as_rdict()
        return self

    # the following method only makes sense when the option to use the
    # CALL_LIKELY_BUILTIN opcode is set. Otherwise it won't even be seen
    # by the annotator
    def impl_get_builtin_indexed(self, w_dict, i):
        key = OPTIMIZED_BUILTINS[i]
        return self.impl_getitem_str(key)

    def impl_popitem(self, w_dict):
        # default implementation
        space = self.space
        iterator = self.impl_iter()
        w_key, w_value = iterator.next()
        if w_key is None:
            raise KeyError
        self.impl_delitem(w_key)
        return w_key, w_value

    # _________________________________________________________________
    # fallback implementation methods


class EmptyIteratorImplementation(object):
    def next(self):
        return (None, None)

class ObjectDictStrategy(DictStrategy):

    cast_to_void_star, cast_from_void_star = rerased.new_erasing_pair("object")
    cast_to_void_star = staticmethod(cast_to_void_star)
    cast_from_void_star = staticmethod(cast_from_void_star)

    def get_empty_storage(self):
       new_dict = r_dict(self.space.eq_w, self.space.hash_w)
       return self.cast_to_void_star(new_dict)

    def setdefault(self, w_dict, w_key, w_default):
        return self.cast_from_void_star(w_dict.dstorage).setdefault(w_key, w_default)

    def setitem(self, w_dict, w_key, w_value):
        self.cast_from_void_star(w_dict.dstorage)[w_key] = w_value

    def setitem_str(self, w_dict, key, w_value):
        return w_dict.setitem(self.space.wrap(key), w_value)

    def delitem(self, w_dict, w_key):
        del self.cast_from_void_star(w_dict.dstorage)[w_key]

    def length(self, w_dict):
        return len(self.cast_from_void_star(w_dict.dstorage))

    def getitem(self, w_dict, w_key):
        return self.cast_from_void_star(w_dict.dstorage).get(w_key, None)

    def getitem_str(self, w_dict, key):
        return self.getitem(w_dict, self.space.wrap(key))

    def iter(self, w_dict):
        return RDictIteratorImplementation(self.space, w_dict)

    def keys(self, w_dict):
        return self.cast_from_void_star(w_dict.dstorage).keys()

    def values(self, w_dict):
        return self.cast_from_void_star(w_dict.dstorage).values()

    def items(self, w_dict):
        return [self.space.newtuple([w_key, w_val])
                    for w_key, w_val in self.cast_from_void_star(w_dict.dstorage).iteritems()]

    def popitem(self, w_dict):
        return self.cast_from_void_star(w_dict.dstorage).popitem()


registerimplementation(W_DictMultiObject)

# DictImplementation lattice
# XXX fix me

# Iterator Implementation base classes

class IteratorImplementation(object):
    def __init__(self, space, implementation):
        self.space = space
        self.dictimplementation = implementation
        self.len = implementation.length()
        self.pos = 0

    def next(self):
        if self.dictimplementation is None:
            return None, None
        if self.len != self.dictimplementation.length():
            self.len = -1   # Make this error state sticky
            raise OperationError(self.space.w_RuntimeError,
                     self.space.wrap("dictionary changed size during iteration"))
        # look for the next entry
        if self.pos < self.len:
            result = self.next_entry()
            self.pos += 1
            return result
        # no more entries
        self.dictimplementation = None
        return None, None

    def next_entry(self):
        """ Purely abstract method
        """
        raise NotImplementedError

    def length(self):
        if self.dictimplementation is not None:
            return self.len - self.pos
        return 0



# concrete subclasses of the above

class StringDictStrategy(DictStrategy):

    cast_to_void_star, cast_from_void_star = rerased.new_erasing_pair("string")
    cast_to_void_star = staticmethod(cast_to_void_star)
    cast_from_void_star = staticmethod(cast_from_void_star)

    def __init__(self, space):
        self.space = space

    def get_empty_storage(self):
       return self.cast_to_void_star({})

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.setitem_str(w_dict, self.space.str_w(w_key), w_value)
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.setitem(w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        self.cast_from_void_star(w_dict.dstorage)[key] = w_value

    def setdefault(self, w_dict, w_key, w_default):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            return self.cast_from_void_star(w_dict.dstorage).setdefault(space.str_w(w_key), w_default)
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.setdefault(w_key, w_default)

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            del self.cast_from_void_star(w_dict.dstorage)[space.str_w(w_key)]
            return
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.delitem(w_key)

    def length(self, w_dict):
        return len(self.cast_from_void_star(w_dict.dstorage))

    def getitem_str(self, w_dict, key):
        return self.cast_from_void_star(w_dict.dstorage).get(key, None)

    def getitem(self, w_dict, w_key):
        space = self.space
        # -- This is called extremely often.  Hack for performance --
        if type(w_key) is space.StringObjectCls:
            return self.getitem_str(w_dict, w_key.unwrap(space))
        # -- End of performance hack --
        w_lookup_type = space.type(w_key)
        if space.is_w(w_lookup_type, space.w_str):
            return self.getitem_str(w_dict, space.str_w(w_key))
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.getitem(w_key)

    def iter(self, w_dict):
        return StrIteratorImplementation(self.space, w_dict)

    def keys(self, w_dict):
        space = self.space
        return [space.wrap(key) for key in self.cast_from_void_star(w_dict.dstorage).iterkeys()]

    def values(self, w_dict):
        return self.cast_from_void_star(w_dict.dstorage).values()

    def items(self, w_dict):
        space = self.space
        dict_w = self.cast_from_void_star(w_dict.dstorage)
        return [space.newtuple([space.wrap(key), w_value])
                    for (key, w_value) in dict_w.iteritems()]

    def popitem(self, w_dict):
        key, value = self.cast_from_void_star(w_dict.dstorage).popitem()
        return (self.space.wrap(key), value)

    def clear(self, w_dict):
        self.cast_from_void_star(w_dict.dstorage).clear()

    def switch_to_object_strategy(self, w_dict):
        d = self.cast_from_void_star(w_dict.dstorage)
        strategy = self.space.fromcache(ObjectDictStrategy)
        d_new = strategy.cast_from_void_star(strategy.get_empty_storage())
        for key, value in d.iteritems():
            d_new[self.space.wrap(key)] = value
        w_dict.strategy = strategy
        w_dict.dstorage = strategy.cast_to_void_star(d_new)

    def _as_rdict(self):
        r_dict_content = self.initialize_as_rdict()
        for k, w_v in self.content.items():
            r_dict_content[self.space.wrap(k)] = w_v
        self._clear_fields()
        return self

    def _clear_fields(self):
        self.content = None

class StrIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        dict_w = dictimplementation.strategy.cast_from_void_star(dictimplementation.dstorage)
        self.iterator = dict_w.iteritems()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for str, w_value in self.iterator:
            return self.space.wrap(str), w_value
        else:
            return None, None


class WaryDictStrategy(StringDictStrategy):
    def __init__(self, space):
        StringDictStrategy.__init__(self, space)
        self.shadowed = [None] * len(BUILTIN_TO_INDEX)

    def setitem_str(self, w_dict, key, w_value):
        i = BUILTIN_TO_INDEX.get(key, -1)
        if i != -1:
            self.shadowed[i] = w_value
        self.cast_from_void_star(w_dict.dstorage)[key] = w_value
        #self.content[key] = w_value

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            del self.cast_from_void_star(w_dict.dstorage)[key]
            i = BUILTIN_TO_INDEX.get(key, -1)
            if i != -1:
                self.shadowed[i] = None
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().impl_fallback_delitem(w_key)

    def get_builtin_indexed(self, w_dict, i):
        return self.shadowed[i]


class RDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        d = dictimplementation.strategy.cast_from_void_star(dictimplementation.dstorage)
        self.iterator = d.iteritems()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for item in self.iterator:
            return item
        else:
            return None, None



# XXX fix this thing
import time

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

class MeasuringDictImplementation(W_DictMultiObject):
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

    def impl_setitem(self, w_dict, w_key, w_value):
        if not self.info.seen_non_string_in_write and not self._is_str(w_key):
            self.info.seen_non_string_in_write = True
            self.info.size_on_non_string_seen_in_write = len(self.content)
        self.info.setitems += 1
        self.info.writes += 1
        self.content[w_key] = w_value
        self.info.maxcontents = max(self.info.maxcontents, len(self.content))
    def impl_setitem_str(self, w_dict, key, w_value):
        self.info.setitem_strs += 1
        self.impl_setitem(self.space.wrap(key), w_value)
    def impl_delitem(self, w_dict, w_key):
        if not self.info.seen_non_string_in_write \
               and not self.info.seen_non_string_in_read_first \
               and not self._is_str(w_key):
            self.info.seen_non_string_in_read_first = True
            self.info.size_on_non_string_seen_in_read = len(self.content)
        self.info.delitems += 1
        self.info.writes += 1
        del self.content[w_key]

    def impl_length(self, w_dict):
        self.info.lengths += 1
        return len(self.content)
    def impl_getitem_str(self, w_dict, key):
        return self.impl_getitem(self.space.wrap(key))
    def impl_getitem(self, w_dict, w_key):
        self.info.gets += 1
        self._read(w_key)
        return self.content.get(w_key, None)

    def impl_iteritems(self, w_dict):
        self.info.iteritems += 1
        self.info.iterations += 1
        return RDictItemIteratorImplementation(self.space, self)
    def impl_iterkeys(self, w_dict):
        self.info.iterkeys += 1
        self.info.iterations += 1
        return RDictKeyIteratorImplementation(self.space, self)
    def impl_itervalues(self, w_dict):
        self.info.itervalues += 1
        self.info.iterations += 1
        return RDictValueIteratorImplementation(self.space, self)

    def impl_keys(self, w_dict):
        self.info.keys += 1
        self.info.listings += 1
        return self.content.keys()
    def impl_values(self, w_dict):
        self.info.values += 1
        self.info.listings += 1
        return self.content.values()
    def impl_items(self, w_dict):
        self.info.items += 1
        self.info.listings += 1
        return [self.space.newtuple([w_key, w_val])
                    for w_key, w_val in self.content.iteritems()]


_example = DictInfo()
del DictInfo._dict_infos[-1]
tmpl = 'os.write(fd, "%(attr)s" + ": " + str(info.%(attr)s) + "\\n")'
bodySrc = []
for attr in sorted(_example.__dict__):
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



init_signature = Signature(['seq_or_map'], None, 'kwargs')
init_defaults = [None]

def update1(space, w_dict, w_data):
    if space.findattr(w_data, space.wrap("keys")) is None:
        # no 'keys' method, so we assume it is a sequence of pairs
        for w_pair in space.listview(w_data):
            pair = space.fixedview(w_pair)
            if len(pair) != 2:
                raise OperationError(space.w_ValueError,
                             space.wrap("sequence of pairs expected"))
            w_key, w_value = pair
            w_dict.setitem(w_key, w_value)
    else:
        if isinstance(w_data, W_DictMultiObject):    # optimization case only
            update1_dict_dict(space, w_dict, w_data)
        else:
            # general case -- "for k in o.keys(): dict.__setitem__(d, k, o[k])"
            w_keys = space.call_method(w_data, "keys")
            for w_key in space.listview(w_keys):
                w_value = space.getitem(w_data, w_key)
                w_dict.setitem(w_key, w_value)

def update1_dict_dict(space, w_dict, w_data):
    iterator = w_data.iter()
    while 1:
        w_key, w_value = iterator.next()
        if w_key is None:
            break
        w_dict.setitem(w_key, w_value)

def init_or_update(space, w_dict, __args__, funcname):
    w_src, w_kwds = __args__.parse_obj(
            None, funcname,
            init_signature, # signature
            init_defaults)  # default argument
    if w_src is not None:
        update1(space, w_dict, w_src)
    if space.is_true(w_kwds):
        update1(space, w_dict, w_kwds)

def init__DictMulti(space, w_dict, __args__):
    init_or_update(space, w_dict, __args__, 'dict')

def dict_update__DictMulti(space, w_dict, __args__):
    init_or_update(space, w_dict, __args__, 'dict.update')

def getitem__DictMulti_ANY(space, w_dict, w_key):
    w_value = w_dict.getitem(w_key)
    if w_value is not None:
        return w_value

    w_missing_item = w_dict.missing_method(space, w_key)
    if w_missing_item is not None:
        return w_missing_item

    space.raise_key_error(w_key)

def setitem__DictMulti_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    w_dict.setitem(w_newkey, w_newvalue)

def delitem__DictMulti_ANY(space, w_dict, w_key):
    try:
        w_dict.delitem(w_key)
    except KeyError:
        space.raise_key_error(w_key)

def len__DictMulti(space, w_dict):
    return space.wrap(w_dict.length())

def contains__DictMulti_ANY(space, w_dict, w_key):
    return space.newbool(w_dict.getitem(w_key) is not None)

dict_has_key__DictMulti_ANY = contains__DictMulti_ANY

def iter__DictMulti(space, w_dict):
    return W_DictMultiIterObject(space, w_dict.iter(), KEYSITER)

def eq__DictMulti_DictMulti(space, w_left, w_right):
    if space.is_w(w_left, w_right):
        return space.w_True

    if w_left.length() != w_right.length():
        return space.w_False
    iteratorimplementation = w_left.iter()
    while 1:
        w_key, w_val = iteratorimplementation.next()
        if w_key is None:
            break
        w_rightval = w_right.getitem(w_key)
        if w_rightval is None:
            return space.w_False
        if not space.eq_w(w_val, w_rightval):
            return space.w_False
    return space.w_True

def characterize(space, w_a, w_b):
    """ (similar to CPython)
    returns the smallest key in acontent for which b's value is different or absent and this value """
    w_smallest_diff_a_key = None
    w_its_value = None
    iteratorimplementation = w_a.iter()
    while 1:
        w_key, w_val = iteratorimplementation.next()
        if w_key is None:
            break
        if w_smallest_diff_a_key is None or space.is_true(space.lt(w_key, w_smallest_diff_a_key)):
            w_bvalue = w_b.getitem(w_key)
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
    if w_left.length() < w_right.length():
        return space.w_True
    if w_left.length() > w_right.length():
        return space.w_False

    # Same size
    w_leftdiff, w_leftval = characterize(space, w_left, w_right)
    if w_leftdiff is None:
        return space.w_False
    w_rightdiff, w_rightval = characterize(space, w_right, w_left)
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
    w_new = W_DictMultiObject.allocate_and_init_instance(space)
    update1_dict_dict(space, w_new, w_self)
    return w_new

def dict_items__DictMulti(space, w_self):
    return space.newlist(w_self.items())

def dict_keys__DictMulti(space, w_self):
    return space.newlist(w_self.keys())

def dict_values__DictMulti(space, w_self):
    return space.newlist(w_self.values())

def dict_iteritems__DictMulti(space, w_self):
    return W_DictMultiIterObject(space, w_self.iter(), ITEMSITER)

def dict_iterkeys__DictMulti(space, w_self):
    return W_DictMultiIterObject(space, w_self.iter(), KEYSITER)

def dict_itervalues__DictMulti(space, w_self):
    return W_DictMultiIterObject(space, w_self.iter(), VALUESITER)

def dict_viewitems__DictMulti(space, w_self):
    return W_DictViewItemsObject(space, w_self)

def dict_viewkeys__DictMulti(space, w_self):
    return W_DictViewKeysObject(space, w_self)

def dict_viewvalues__DictMulti(space, w_self):
    return W_DictViewValuesObject(space, w_self)

def dict_clear__DictMulti(space, w_self):
    w_self.clear()

def dict_get__DictMulti_ANY_ANY(space, w_dict, w_key, w_default):
    w_value = w_dict.getitem(w_key)
    if w_value is not None:
        return w_value
    else:
        return w_default

def dict_setdefault__DictMulti_ANY_ANY(space, w_dict, w_key, w_default):
    return w_dict.setdefault(w_key, w_default)

def dict_pop__DictMulti_ANY(space, w_dict, w_key, defaults_w):
    len_defaults = len(defaults_w)
    if len_defaults > 1:
        raise operationerrfmt(space.w_TypeError,
                              "pop expected at most 2 arguments, got %d",
                              1 + len_defaults)
    w_item = w_dict.getitem(w_key)
    if w_item is None:
        if len_defaults > 0:
            return defaults_w[0]
        else:
            space.raise_key_error(w_key)
    else:
        w_dict.delitem(w_key)
        return w_item

def dict_popitem__DictMulti(space, w_dict):
    try:
        w_key, w_value = w_dict.popitem()
    except KeyError:
        raise OperationError(space.w_KeyError,
                             space.wrap("popitem(): dictionary is empty"))
    return space.newtuple([w_key, w_value])


# ____________________________________________________________
# Iteration


KEYSITER = 0
ITEMSITER = 1
VALUESITER = 2

class W_DictMultiIterObject(W_Object):
    from pypy.objspace.std.dicttype import dictiter_typedef as typedef

    def __init__(w_self, space, iteratorimplementation, itertype):
        w_self.space = space
        w_self.iteratorimplementation = iteratorimplementation
        w_self.itertype = itertype

registerimplementation(W_DictMultiIterObject)

def iter__DictMultiIterObject(space, w_dictiter):
    return w_dictiter

def next__DictMultiIterObject(space, w_dictiter):
    iteratorimplementation = w_dictiter.iteratorimplementation
    w_key, w_value = iteratorimplementation.next()
    if w_key is not None:
        itertype = w_dictiter.itertype
        if itertype == KEYSITER:
            return w_key
        elif itertype == VALUESITER:
            return w_value
        elif itertype == ITEMSITER:
            return space.newtuple([w_key, w_value])
        else:
            assert 0, "should be unreachable"
    raise OperationError(space.w_StopIteration, space.w_None)

# ____________________________________________________________
# Views

class W_DictViewObject(W_Object):
    def __init__(w_self, space, w_dict):
        w_self.w_dict = w_dict

class W_DictViewKeysObject(W_DictViewObject):
    from pypy.objspace.std.dicttype import dict_keys_typedef as typedef
registerimplementation(W_DictViewKeysObject)

class W_DictViewItemsObject(W_DictViewObject):
    from pypy.objspace.std.dicttype import dict_items_typedef as typedef
registerimplementation(W_DictViewItemsObject)

class W_DictViewValuesObject(W_DictViewObject):
    from pypy.objspace.std.dicttype import dict_values_typedef as typedef
registerimplementation(W_DictViewValuesObject)

def len__DictViewKeys(space, w_dictview):
    return space.len(w_dictview.w_dict)
len__DictViewItems = len__DictViewValues = len__DictViewKeys

def iter__DictViewKeys(space, w_dictview):
    return dict_iterkeys__DictMulti(space, w_dictview.w_dict)
def iter__DictViewItems(space, w_dictview):
    return dict_iteritems__DictMulti(space, w_dictview.w_dict)
def iter__DictViewValues(space, w_dictview):
    return dict_itervalues__DictMulti(space, w_dictview.w_dict)

def all_contained_in(space, w_dictview, w_otherview):
    w_iter = space.iter(w_dictview)
    assert isinstance(w_iter, W_DictMultiIterObject)

    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        if not space.is_true(space.contains(w_otherview, w_item)):
            return space.w_False

    return space.w_True

def eq__DictViewKeys_DictViewKeys(space, w_dictview, w_otherview):
    if space.eq_w(space.len(w_dictview), space.len(w_otherview)):
        return all_contained_in(space, w_dictview, w_otherview)
    return space.w_False
eq__DictViewKeys_settypedef = eq__DictViewKeys_DictViewKeys

eq__DictViewKeys_DictViewItems = eq__DictViewKeys_DictViewKeys
eq__DictViewItems_DictViewItems = eq__DictViewKeys_DictViewKeys
eq__DictViewItems_settypedef = eq__DictViewItems_DictViewItems

def repr__DictViewKeys(space, w_dictview):
    w_seq = space.call_function(space.w_list, w_dictview)
    w_repr = space.repr(w_seq)
    return space.wrap("%s(%s)" % (space.type(w_dictview).getname(space, "?"),
                                  space.str_w(w_repr)))
repr__DictViewItems  = repr__DictViewKeys
repr__DictViewValues = repr__DictViewKeys

def and__DictViewKeys_DictViewKeys(space, w_dictview, w_otherview):
    w_set = space.call_function(space.w_set, w_dictview)
    space.call_method(w_set, "intersection_update", w_otherview)
    return w_set
and__DictViewKeys_settypedef = and__DictViewKeys_DictViewKeys
and__DictViewItems_DictViewItems = and__DictViewKeys_DictViewKeys
and__DictViewItems_settypedef = and__DictViewKeys_DictViewKeys

def or__DictViewKeys_DictViewKeys(space, w_dictview, w_otherview):
    w_set = space.call_function(space.w_set, w_dictview)
    space.call_method(w_set, "update", w_otherview)
    return w_set
or__DictViewKeys_settypedef = or__DictViewKeys_DictViewKeys
or__DictViewItems_DictViewItems = or__DictViewKeys_DictViewKeys
or__DictViewItems_settypedef = or__DictViewKeys_DictViewKeys

def xor__DictViewKeys_DictViewKeys(space, w_dictview, w_otherview):
    w_set = space.call_function(space.w_set, w_dictview)
    space.call_method(w_set, "symmetric_difference_update", w_otherview)
    return w_set
xor__DictViewKeys_settypedef = xor__DictViewKeys_DictViewKeys
xor__DictViewItems_DictViewItems = xor__DictViewKeys_DictViewKeys
xor__DictViewItems_settypedef = xor__DictViewKeys_DictViewKeys

# ____________________________________________________________

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
