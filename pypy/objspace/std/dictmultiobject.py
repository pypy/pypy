import py, sys
from pypy.objspace.std.objspace import register_all, W_Object
from pypy.objspace.std.objspace import registerimplementation
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.argument import Signature
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

class W_DictMultiObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    r_dict_content = None

    @staticmethod
    def allocate_and_init_instance(space, w_type=None, module=False,
                                   instance=False, classofinstance=None,
                                   from_strdict_shared=None, strdict=False):
        if from_strdict_shared is not None:
            assert w_type is None
            assert not module and not instance and classofinstance is None
            w_self = StrDictImplementation(space)
            w_self.content = from_strdict_shared
            return w_self
        if space.config.objspace.std.withcelldict and module:
            from pypy.objspace.std.celldict import ModuleDictImplementation
            assert w_type is None
            return ModuleDictImplementation(space)
        elif space.config.objspace.opcodes.CALL_LIKELY_BUILTIN and module:
            assert w_type is None
            return WaryDictImplementation(space)
        elif space.config.objspace.std.withdictmeasurement:
            assert w_type is None
            return MeasuringDictImplementation(space)
        elif space.config.objspace.std.withsharingdict and instance:
            from pypy.objspace.std.sharingdict import SharedDictImplementation
            assert w_type is None
            return SharedDictImplementation(space)
        elif (space.config.objspace.std.withshadowtracking and instance and
                classofinstance is not None):
            assert w_type is None
            return ShadowDetectingDictImplementation(space, classofinstance)
        elif instance or strdict or module:
            assert w_type is None
            return StrDictImplementation(space)
        else:
            if w_type is None:
                w_type = space.w_dict
            w_self = space.allocate_instance(W_DictMultiObject, w_type)
            W_DictMultiObject.__init__(w_self, space)
            w_self.initialize_as_rdict()
            return w_self

    def __init__(self, space):
        self.space = space

    def initialize_as_rdict(self):
        assert self.r_dict_content is None
        self.r_dict_content = r_dict(self.space.eq_w, self.space.hash_w)
        return self.r_dict_content
        

    def initialize_content(w_self, list_pairs_w):
        for w_k, w_v in list_pairs_w:
            w_self.setitem(w_k, w_v)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s()" % (w_self.__class__.__name__, )

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
            return space.call_function(w_missing, w_dict, w_key)
        else:
            return None

    def set_str_keyed_item(w_dict, key, w_value, shadows_type=True):
        w_dict.setitem_str(key, w_value, shadows_type)

    # _________________________________________________________________ 
    # implementation methods
    def impl_getitem(self, w_key):
        #return w_value or None
        raise NotImplementedError("abstract base class")

    def impl_getitem_str(self, w_key):
        #return w_value or None
        raise NotImplementedError("abstract base class")

    def impl_setitem_str(self,  key, w_value, shadows_type=True):
        raise NotImplementedError("abstract base class")

    def impl_setitem(self,  w_key, w_value):
        raise NotImplementedError("abstract base class")

    def impl_delitem(self, w_key):
        raise NotImplementedError("abstract base class")
 
    def impl_length(self):
        raise NotImplementedError("abstract base class")

    def impl_iter(self):
        raise NotImplementedError("abstract base class")

    def impl_clear(self):
        raise NotImplementedError("abstract base class")

    def impl_keys(self):
        iterator = self.impl_iter()
        result = []
        while 1:
            w_key, w_value = iterator.next()
            if w_key is not None:
                result.append(w_key)
            else:
                return result
    def impl_values(self):
        iterator = self.impl_iter()
        result = []
        while 1:
            w_key, w_value = iterator.next()
            if w_value is not None:
                result.append(w_value)
            else:
                return result
    def impl_items(self):
        iterator = self.impl_iter()
        result = []
        while 1:
            w_key, w_value = iterator.next()
            if w_key is not None:
                result.append(self.space.newtuple([w_key, w_value]))
            else:
                return result

    # the following method only makes sense when the option to use the
    # CALL_LIKELY_BUILTIN opcode is set. Otherwise it won't even be seen
    # by the annotator
    def impl_get_builtin_indexed(self, i):
        key = OPTIMIZED_BUILTINS[i]
        return self.impl_getitem_str(key)

    # this method will only be seen whan a certain config option is used
    def impl_shadows_anything(self):
        return True

    def impl_set_shadows_anything(self):
        pass

    # _________________________________________________________________
    # fallback implementation methods

    def impl_fallback_setitem(self, w_key, w_value):
        self.r_dict_content[w_key] = w_value

    def impl_fallback_setitem_str(self, key, w_value, shadows_type=True):
        return self.impl_fallback_setitem(self.space.wrap(key), w_value)

    def impl_fallback_delitem(self, w_key):
        del self.r_dict_content[w_key]
        
    def impl_fallback_length(self):
        return len(self.r_dict_content)

    def impl_fallback_getitem(self, w_key):
        return self.r_dict_content.get(w_key, None)

    def impl_fallback_getitem_str(self, key):
        return self.r_dict_content.get(self.space.wrap(key), None)

    def impl_fallback_iter(self):
        return RDictIteratorImplementation(self.space, self)

    def impl_fallback_keys(self):
        return self.r_dict_content.keys()
    def impl_fallback_values(self):
        return self.r_dict_content.values()
    def impl_fallback_items(self):
        return [self.space.newtuple([w_key, w_val])
                    for w_key, w_val in self.r_dict_content.iteritems()]

    def impl_fallback_clear(self):
        self.r_dict_content.clear()

    def impl_fallback_get_builtin_indexed(self, i):
        key = OPTIMIZED_BUILTINS[i]
        return self.impl_fallback_getitem_str(key)

    def impl_fallback_shadows_anything(self):
        return True

    def impl_fallback_set_shadows_anything(self):
        pass


implementation_methods = [
    ("getitem", 1),
    ("getitem_str", 1),
    ("length", 0),
    ("setitem_str", 3),
    ("setitem", 2),
    ("delitem", 1),
    ("iter", 0),
    ("items", 0),
    ("values", 0),
    ("keys", 0),
    ("clear", 0),
    ("get_builtin_indexed", 1),
    ("shadows_anything", 0),
    ("set_shadows_anything", 0),
]


def _make_method(name, implname, fallback, numargs):
    args = ", ".join(["a" + str(i) for i in range(numargs)])
    code = """def %s(self, %s):
        if self.r_dict_content is not None:
            return self.%s(%s)
        return self.%s(%s)""" % (name, args, fallback, args, implname, args)
    d = {}
    exec py.code.Source(code).compile() in d
    implementation_method = d[name]
    implementation_method.func_defaults = getattr(W_DictMultiObject, implname).func_defaults
    return implementation_method

def _install_methods():
    for name, numargs in implementation_methods:
        implname = "impl_" + name
        fallbackname = "impl_fallback_" + name
        func = _make_method(name, implname, fallbackname, numargs)
        setattr(W_DictMultiObject, name, func)
_install_methods()

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

class StrDictImplementation(W_DictMultiObject):
    def __init__(self, space):
        self.space = space
        self.content = {}
        
    def impl_setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            self._as_rdict().setitem(w_key, w_value)

    def impl_setitem_str(self, key, w_value, shadows_type=True):
        self.content[key] = w_value

    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            del self.content[space.str_w(w_key)]
            return
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().delitem(w_key)
        
    def impl_length(self):
        return len(self.content)

    def impl_getitem_str(self, key):
        return self.content.get(key, None)

    def impl_getitem(self, w_key):
        space = self.space
        # -- This is called extremely often.  Hack for performance --
        if type(w_key) is space.StringObjectCls:
            return self.impl_getitem_str(w_key.unwrap(space))
        # -- End of performance hack --
        w_lookup_type = space.type(w_key)
        if space.is_w(w_lookup_type, space.w_str):
            return self.impl_getitem_str(space.str_w(w_key))
        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().getitem(w_key)

    def impl_iter(self):
        return StrIteratorImplementation(self.space, self)

    def impl_keys(self):
        space = self.space
        return [space.wrap(key) for key in self.content.iterkeys()]

    def impl_values(self):
        return self.content.values()

    def impl_items(self):
        space = self.space
        return [space.newtuple([space.wrap(key), w_value])
                    for (key, w_value) in self.content.iteritems()]

    def impl_clear(self):
        self.content.clear()


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
        self.iterator = dictimplementation.content.iteritems()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for str, w_value in self.iterator:
            return self.space.wrap(str), w_value
        else:
            return None, None


class ShadowDetectingDictImplementation(StrDictImplementation):
    def __init__(self, space, w_type):
        StrDictImplementation.__init__(self, space)
        self.w_type = w_type
        self.original_version_tag = w_type.version_tag()
        if self.original_version_tag is None:
            self._shadows_anything = True
        else:
            self._shadows_anything = False

    def impl_setitem_str(self, key, w_value, shadows_type=True):
        if shadows_type:
            self._shadows_anything = True
        StrDictImplementation.impl_setitem_str(
            self, key, w_value, shadows_type)

    def impl_setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            if not self._shadows_anything:
                w_obj = self.w_type.lookup(space.str_w(w_key))
                if w_obj is not None:
                    self._shadows_anything = True
            StrDictImplementation.impl_setitem_str(
                self, self.space.str_w(w_key), w_value, False)
        else:
            self._as_rdict().setitem(w_key, w_value)

    def impl_shadows_anything(self):
        return (self._shadows_anything or 
                self.w_type.version_tag() is not self.original_version_tag)

    def impl_set_shadows_anything(self):
        self._shadows_anything = True

class WaryDictImplementation(StrDictImplementation):
    def __init__(self, space):
        StrDictImplementation.__init__(self, space)
        self.shadowed = [None] * len(BUILTIN_TO_INDEX)

    def impl_setitem_str(self, key, w_value, shadows_type=True):
        i = BUILTIN_TO_INDEX.get(key, -1)
        if i != -1:
            self.shadowed[i] = w_value
        self.content[key] = w_value

    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            del self.content[key]
            i = BUILTIN_TO_INDEX.get(key, -1)
            if i != -1:
                self.shadowed[i] = None
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().delitem(w_key)

    def impl_get_builtin_indexed(self, i):
        return self.shadowed[i]


class RDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.r_dict_content.iteritems()

    def next_entry(self):
        # note that this 'for' loop only runs once, at most
        for item in self.iterator:
            return item
        else:
            return None, None



# XXX fix this thing
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

    def impl_setitem(self, w_key, w_value):
        if not self.info.seen_non_string_in_write and not self._is_str(w_key):
            self.info.seen_non_string_in_write = True
            self.info.size_on_non_string_seen_in_write = len(self.content)
        self.info.setitems += 1
        self.info.writes += 1
        self.content[w_key] = w_value
        self.info.maxcontents = max(self.info.maxcontents, len(self.content))
    def impl_setitem_str(self, key, w_value, shadows_type=True):
        self.info.setitem_strs += 1
        self.impl_setitem(self.space.wrap(key), w_value)
    def impl_delitem(self, w_key):
        if not self.info.seen_non_string_in_write \
               and not self.info.seen_non_string_in_read_first \
               and not self._is_str(w_key):
            self.info.seen_non_string_in_read_first = True
            self.info.size_on_non_string_seen_in_read = len(self.content)
        self.info.delitems += 1
        self.info.writes += 1
        del self.content[w_key]

    def impl_length(self):
        self.info.lengths += 1
        return len(self.content)
    def impl_getitem_str(self, key):
        return self.impl_getitem(self.space.wrap(key))
    def impl_getitem(self, w_key):
        self.info.gets += 1
        self._read(w_key)
        return self.content.get(w_key, None)

    def impl_iteritems(self):
        self.info.iteritems += 1
        self.info.iterations += 1
        return RDictItemIteratorImplementation(self.space, self)
    def impl_iterkeys(self):
        self.info.iterkeys += 1
        self.info.iterations += 1
        return RDictKeyIteratorImplementation(self.space, self)
    def impl_itervalues(self):
        self.info.itervalues += 1
        self.info.iterations += 1
        return RDictValueIteratorImplementation(self.space, self)

    def impl_keys(self):
        self.info.keys += 1
        self.info.listings += 1
        return self.content.keys()
    def impl_values(self):
        self.info.values += 1
        self.info.listings += 1
        return self.content.values()
    def impl_items(self):
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



init_signature = Signature(['seq_or_map'], None, 'kwargs')
init_defaults = [None]

def init__DictMulti(space, w_dict, __args__):
    w_src, w_kwds = __args__.parse_obj(
            None, 'dict',
            init_signature, # signature
            init_defaults)                           # default argument
    if w_src is None:
        pass
    elif space.findattr(w_src, space.wrap("keys")) is None:
        list_of_w_pairs = space.listview(w_src)
        for w_pair in list_of_w_pairs:
            pair = space.fixedview(w_pair)
            if len(pair)!=2:
                raise OperationError(space.w_ValueError,
                             space.wrap("dict() takes a sequence of pairs"))
            w_k, w_v = pair
            w_dict.setitem(w_k, w_v)
    else:
        if space.is_true(w_src):
            from pypy.objspace.std.dicttype import update1
            update1(space, w_dict, w_src)
    if space.is_true(w_kwds):
        from pypy.objspace.std.dicttype import update1
        update1(space, w_dict, w_kwds)

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
    from pypy.objspace.std.dicttype import update1
    w_new = W_DictMultiObject.allocate_and_init_instance(space)
    update1(space, w_new, w_self)
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

def dict_clear__DictMulti(space, w_self):
    w_self.clear()

def dict_get__DictMulti_ANY_ANY(space, w_dict, w_key, w_default):
    w_value = w_dict.getitem(w_key)
    if w_value is not None:
        return w_value
    else:
        return w_default

def dict_pop__DictMulti_ANY(space, w_dict, w_key, w_defaults):
    defaults = space.listview(w_defaults)
    len_defaults = len(defaults)
    if len_defaults > 1:
        raise operationerrfmt(space.w_TypeError,
                              "pop expected at most 2 arguments, got %d",
                              1 + len_defaults)
    w_item = w_dict.getitem(w_key)
    if w_item is None:
        if len_defaults > 0:
            return defaults[0]
        else:
            space.raise_key_error(w_key)
    else:
        w_dict.delitem(w_key)
        return w_item

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
                for k, v in dict.items(d):
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
    if w_dict.length() == 0:
        return space.wrap('{}')
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return dictrepr(space, w_currently_in_repr, w_dict)


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

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
