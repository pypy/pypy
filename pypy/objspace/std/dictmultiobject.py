import py, sys
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.settype import set_typedef as settypedef
from pypy.objspace.std.frozensettype import frozenset_typedef as frozensettypedef
from pypy.interpreter import gateway
from pypy.interpreter.argument import Signature
from pypy.interpreter.error import OperationError, operationerrfmt

from pypy.rlib.objectmodel import r_dict, we_are_translated, specialize,\
     newlist_hint
from pypy.rlib.debug import mark_dict_non_null
from pypy.tool.sourcetools import func_with_new_name

from pypy.rlib import rerased
from pypy.rlib import jit

def _is_str(space, w_key):
    return space.is_w(space.type(w_key), space.w_str)

def _never_equal_to_string(space, w_lookup_type):
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


DICT_CUTOFF = 5

@specialize.call_location()
def w_dict_unrolling_heuristic(w_dct):
    """ In which cases iterating over dict items can be unrolled.
    Note that w_dct is an instance of W_DictMultiObject, not necesarilly
    an actual dict
    """
    return jit.isvirtual(w_dct) or (jit.isconstant(w_dct) and
                                    w_dct.length() <= DICT_CUTOFF)

class W_DictMultiObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    @staticmethod
    def allocate_and_init_instance(space, w_type=None, module=False,
                                   instance=False, strdict=False, kwargs=False):

        if space.config.objspace.std.withcelldict and module:
            from pypy.objspace.std.celldict import ModuleDictStrategy
            assert w_type is None
            # every module needs its own strategy, because the strategy stores
            # the version tag
            strategy = ModuleDictStrategy(space)

        elif instance or strdict or module:
            assert w_type is None
            strategy = space.fromcache(StringDictStrategy)

        elif kwargs:
            assert w_type is None
            from pypy.objspace.std.kwargsdict import EmptyKwargsDictStrategy
            strategy = space.fromcache(EmptyKwargsDictStrategy)
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

    def view_as_kwargs(self):
        return self.strategy.view_as_kwargs(self)

def _add_indirections():
    dict_methods = "setitem setitem_str getitem \
                    getitem_str delitem length \
                    clear w_keys values \
                    items iterkeys itervalues iteritems setdefault \
                    popitem listview_str listview_int".split()

    def make_method(method):
        def f(self, *args):
            return getattr(self.strategy, method)(self, *args)
        f.func_name = method
        return f

    def view_as_kwargs(self):
        return self.strategy.view_as_kwargs(self)

    for method in dict_methods:
        setattr(W_DictMultiObject, method, make_method(method))

_add_indirections()

class DictStrategy(object):

    def __init__(self, space):
        self.space = space

    def get_empty_storage(self):
        raise NotImplementedError

    def w_keys(self, w_dict):
        iterator = self.iterkeys(w_dict)
        result = newlist_hint(self.length(w_dict))
        while 1:
            w_key = iterator.next_key()
            if w_key is not None:
                result.append(w_key)
            else:
                return self.space.newlist(result)

    def values(self, w_dict):
        iterator = self.itervalues(w_dict)
        result = newlist_hint(self.length(w_dict))
        while 1:
            w_value = iterator.next_value()
            if w_value is not None:
                result.append(w_value)
            else:
                return result

    def items(self, w_dict):
        iterator = self.iteritems(w_dict)
        result = newlist_hint(self.length(w_dict))
        while 1:
            w_key, w_value = iterator.next_item()
            if w_key is not None:
                result.append(self.space.newtuple([w_key, w_value]))
            else:
                return result

    def popitem(self, w_dict):
        # this is a bad implementation: if we call popitem() repeatedly,
        # it ends up taking n**2 time, because the next() calls below
        # will take longer and longer.  But all interesting strategies
        # provide a better one.
        space = self.space
        iterator = self.iteritems(w_dict)
        w_key, w_value = iterator.next_item()
        self.delitem(w_dict, w_key)
        return (w_key, w_value)

    def clear(self, w_dict):
        strategy = self.space.fromcache(EmptyDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.strategy = strategy
        w_dict.dstorage = storage

    def listview_str(self, w_dict):
        return None

    def listview_int(self, w_dict):
        return None

    def view_as_kwargs(self, w_dict):
        return (None, None)

class EmptyDictStrategy(DictStrategy):

    erase, unerase = rerased.new_erasing_pair("empty")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def get_empty_storage(self):
       return self.erase(None)

    def switch_to_correct_strategy(self, w_dict, w_key):
        withidentitydict = self.space.config.objspace.std.withidentitydict
        if type(w_key) is self.space.StringObjectCls:
            self.switch_to_string_strategy(w_dict)
            return
        w_type = self.space.type(w_key)
        if self.space.is_w(w_type, self.space.w_int):
            self.switch_to_int_strategy(w_dict)
        elif withidentitydict and w_type.compares_by_identity():
            self.switch_to_identity_strategy(w_dict)
        else:
            self.switch_to_object_strategy(w_dict)

    def switch_to_string_strategy(self, w_dict):
        strategy = self.space.fromcache(StringDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.strategy = strategy
        w_dict.dstorage = storage

    def switch_to_int_strategy(self, w_dict):
        strategy = self.space.fromcache(IntDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.strategy = strategy
        w_dict.dstorage = storage

    def switch_to_identity_strategy(self, w_dict):
        from pypy.objspace.std.identitydict import IdentityDictStrategy
        strategy = self.space.fromcache(IdentityDictStrategy)
        storage = strategy.get_empty_storage()
        w_dict.strategy = strategy
        w_dict.dstorage = storage

    def switch_to_object_strategy(self, w_dict):
        strategy = self.space.fromcache(ObjectDictStrategy)
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
        w_dict.setitem_str(key, w_value)

    def delitem(self, w_dict, w_key):
        # in case the key is unhashable, try to hash it
        self.space.hash(w_key)
        raise KeyError

    def length(self, w_dict):
        return 0

    def clear(self, w_dict):
        return

    def popitem(self, w_dict):
        raise KeyError

    def view_as_kwargs(self, w_dict):
        return ([], [])

    # ---------- iterator interface ----------------

    def getiterkeys(self, w_dict):
        return iter([None])
    getitervalues = getiterkeys
    def getiteritems(self, w_dict):
        return iter([(None, None)])

# Iterator Implementation base classes

def _new_next(TP):
    if TP == 'key' or TP == 'value':
        EMPTY = None
    else:
        EMPTY = None, None
    
    def next(self):
        if self.dictimplementation is None:
            return EMPTY
        if self.len != self.dictimplementation.length():
            self.len = -1   # Make this error state sticky
            raise OperationError(self.space.w_RuntimeError,
                     self.space.wrap("dictionary changed size during iteration"))
        # look for the next entry
        if self.pos < self.len:
            result = getattr(self, 'next_' + TP + '_entry')()
            self.pos += 1
            if self.strategy is self.dictimplementation.strategy:
                return result      # common case
            else:
                # waaa, obscure case: the strategy changed, but not the
                # length of the dict.  The (key, value) pair in 'result'
                # might be out-of-date.  We try to explicitly look up
                # the key in the dict.
                if TP == 'key' or TP == 'value':
                    return result
                w_key = result[0]
                w_value = self.dictimplementation.getitem(w_key)
                if w_value is None:
                    self.len = -1   # Make this error state sticky
                    raise OperationError(self.space.w_RuntimeError,
                        self.space.wrap("dictionary changed during iteration"))
                return (w_key, w_value)
        # no more entries
        self.dictimplementation = None
        return EMPTY
    return func_with_new_name(next, 'next_' + TP)

class BaseIteratorImplementation(object):
    def __init__(self, space, strategy, implementation):
        self.space = space
        self.strategy = strategy
        self.dictimplementation = implementation
        self.len = implementation.length()
        self.pos = 0

    def length(self):
        if self.dictimplementation is not None:
            return self.len - self.pos
        return 0

class BaseKeyIterator(BaseIteratorImplementation):
    next_key = _new_next('key')

class BaseValueIterator(BaseIteratorImplementation):
    next_value = _new_next('value')

class BaseItemIterator(BaseIteratorImplementation):
    next_item = _new_next('item')

def create_iterator_classes(dictimpl, override_next_item=None):
    if not hasattr(dictimpl, 'wrapkey'):
        wrapkey = lambda space, key : key
    else:
        wrapkey = dictimpl.wrapkey.im_func
    if not hasattr(dictimpl, 'wrapvalue'):
        wrapvalue = lambda space, key : key
    else:
        wrapvalue = dictimpl.wrapvalue.im_func
    
    class IterClassKeys(BaseKeyIterator):
        def __init__(self, space, strategy, impl):
            self.iterator = strategy.getiterkeys(impl)
            BaseIteratorImplementation.__init__(self, space, strategy, impl)

        def next_key_entry(self):
            for key in self.iterator:
                return wrapkey(self.space, key)
            else:
                return None

    class IterClassValues(BaseValueIterator):
        def __init__(self, space, strategy, impl):
            self.iterator = strategy.getitervalues(impl)
            BaseIteratorImplementation.__init__(self, space, strategy, impl)

        def next_value_entry(self):
            for value in self.iterator:
                return wrapvalue(self.space, value)
            else:
                return None

    class IterClassItems(BaseItemIterator):
        def __init__(self, space, strategy, impl):
            self.iterator = strategy.getiteritems(impl)
            BaseIteratorImplementation.__init__(self, space, strategy, impl)

        if override_next_item is not None:
            next_item_entry = override_next_item
        else:
            def next_item_entry(self):
                for key, value in self.iterator:
                    return (wrapkey(self.space, key),
                            wrapvalue(self.space, value))
                else:
                    return None, None

    def iterkeys(self, w_dict):
        return IterClassKeys(self.space, self, w_dict)

    def itervalues(self, w_dict):
        return IterClassValues(self.space, self, w_dict)

    def iteritems(self, w_dict):
        return IterClassItems(self.space, self, w_dict)
    dictimpl.iterkeys = iterkeys
    dictimpl.itervalues = itervalues
    dictimpl.iteritems = iteritems

create_iterator_classes(EmptyDictStrategy)

registerimplementation(W_DictMultiObject)

# DictImplementation lattice
# XXX fix me


# concrete subclasses of the above

class AbstractTypedStrategy(object):
    _mixin_ = True

    @staticmethod
    def erase(storage):
        raise NotImplementedError("abstract base class")

    @staticmethod
    def unerase(obj):
        raise NotImplementedError("abstract base class")

    def wrap(self, unwrapped):
        raise NotImplementedError

    def unwrap(self, wrapped):
        raise NotImplementedError

    def is_correct_type(self, w_obj):
        raise NotImplementedError("abstract base class")

    def get_empty_storage(self):
        raise NotImplementedError("abstract base class")

    def _never_equal_to(self, w_lookup_type):
        raise NotImplementedError("abstract base class")

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if self.is_correct_type(w_key):
            self.unerase(w_dict.dstorage)[self.unwrap(w_key)] = w_value
            return
        else:
            self.switch_to_object_strategy(w_dict)
            w_dict.setitem(w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        self.switch_to_object_strategy(w_dict)
        w_dict.setitem(self.space.wrap(key), w_value)

    def setdefault(self, w_dict, w_key, w_default):
        space = self.space
        if self.is_correct_type(w_key):
            return self.unerase(w_dict.dstorage).setdefault(self.unwrap(w_key), w_default)
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.setdefault(w_key, w_default)

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if self.is_correct_type(w_key):
            del self.unerase(w_dict.dstorage)[self.unwrap(w_key)]
            return
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.delitem(w_key)

    def length(self, w_dict):
        return len(self.unerase(w_dict.dstorage))

    def getitem_str(self, w_dict, key):
        return self.getitem(w_dict, self.space.wrap(key))

    def getitem(self, w_dict, w_key):
        space = self.space
        if self.is_correct_type(w_key):
            return self.unerase(w_dict.dstorage).get(self.unwrap(w_key), None)
        elif self._never_equal_to(space.type(w_key)):
            return None
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.getitem(w_key)

    def w_keys(self, w_dict):
        l = [self.wrap(key) for key in self.unerase(w_dict.dstorage).iterkeys()]
        return self.space.newlist(l)

    def values(self, w_dict):
        return self.unerase(w_dict.dstorage).values()

    def items(self, w_dict):
        space = self.space
        dict_w = self.unerase(w_dict.dstorage)
        return [space.newtuple([self.wrap(key), w_value])
                    for (key, w_value) in dict_w.iteritems()]

    def popitem(self, w_dict):
        key, value = self.unerase(w_dict.dstorage).popitem()
        return (self.wrap(key), value)

    def clear(self, w_dict):
        self.unerase(w_dict.dstorage).clear()

    def switch_to_object_strategy(self, w_dict):
        d = self.unerase(w_dict.dstorage)
        strategy = self.space.fromcache(ObjectDictStrategy)
        d_new = strategy.unerase(strategy.get_empty_storage())
        for key, value in d.iteritems():
            d_new[self.wrap(key)] = value
        w_dict.strategy = strategy
        w_dict.dstorage = strategy.erase(d_new)

    # --------------- iterator interface -----------------

    def getiterkeys(self, w_dict):
        return self.unerase(w_dict.dstorage).iterkeys()
    def getitervalues(self, w_dict):
        return self.unerase(w_dict.dstorage).itervalues()
    def getiteritems(self, w_dict):
        return self.unerase(w_dict.dstorage).iteritems()

class ObjectDictStrategy(AbstractTypedStrategy, DictStrategy):

    erase, unerase = rerased.new_erasing_pair("object")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def wrap(self, unwrapped):
        return unwrapped

    def unwrap(self, wrapped):
        return wrapped

    def is_correct_type(self, w_obj):
        return True

    def get_empty_storage(self):
       new_dict = r_dict(self.space.eq_w, self.space.hash_w,
                         force_non_null=True)
       return self.erase(new_dict)

    def _never_equal_to(self, w_lookup_type):
        return False

    def w_keys(self, w_dict):
        return self.space.newlist(self.unerase(w_dict.dstorage).keys())

create_iterator_classes(ObjectDictStrategy)

class StringDictStrategy(AbstractTypedStrategy, DictStrategy):

    erase, unerase = rerased.new_erasing_pair("string")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def wrap(self, unwrapped):
        return self.space.wrap(unwrapped)

    def unwrap(self, wrapped):
        return self.space.str_w(wrapped)

    def is_correct_type(self, w_obj):
        space = self.space
        return space.is_w(space.type(w_obj), space.w_str)

    def get_empty_storage(self):
        res = {}
        mark_dict_non_null(res)
        return self.erase(res)

    def _never_equal_to(self, w_lookup_type):
        return _never_equal_to_string(self.space, w_lookup_type)

    def setitem_str(self, w_dict, key, w_value):
        assert key is not None
        self.unerase(w_dict.dstorage)[key] = w_value

    def getitem(self, w_dict, w_key):
        space = self.space
        # -- This is called extremely often.  Hack for performance --
        if type(w_key) is space.StringObjectCls:
            return self.getitem_str(w_dict, w_key.unwrap(space))
        # -- End of performance hack --
        return AbstractTypedStrategy.getitem(self, w_dict, w_key)

    def getitem_str(self, w_dict, key):
        assert key is not None
        return self.unerase(w_dict.dstorage).get(key, None)

    def listview_str(self, w_dict):
        return self.unerase(w_dict.dstorage).keys()

    def w_keys(self, w_dict):
        return self.space.newlist_str(self.listview_str(w_dict))

    def wrapkey(space, key):
        return space.wrap(key)

    @jit.look_inside_iff(lambda self, w_dict:
                         w_dict_unrolling_heuristic(w_dict))
    def view_as_kwargs(self, w_dict):
        d = self.unerase(w_dict.dstorage)
        l = len(d)
        keys, values = [None] * l, [None] * l
        i = 0
        for key, val in d.iteritems():
            keys[i] = key
            values[i] = val
            i += 1
        return keys, values

create_iterator_classes(StringDictStrategy)


class IntDictStrategy(AbstractTypedStrategy, DictStrategy):
    erase, unerase = rerased.new_erasing_pair("int")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def wrap(self, unwrapped):
        return self.space.wrap(unwrapped)

    def unwrap(self, wrapped):
        return self.space.int_w(wrapped)

    def get_empty_storage(self):
        return self.erase({})

    def is_correct_type(self, w_obj):
        space = self.space
        return space.is_w(space.type(w_obj), space.w_int)

    def _never_equal_to(self, w_lookup_type):
        space = self.space
        # XXX there are many more types
        return (space.is_w(w_lookup_type, space.w_NoneType) or
                space.is_w(w_lookup_type, space.w_str) or
                space.is_w(w_lookup_type, space.w_unicode)
                )

    def listview_int(self, w_dict):
        return self.unerase(w_dict.dstorage).keys()

    def wrapkey(space, key):
        return space.wrap(key)

    # XXX there is no space.newlist_int yet to implement w_keys more efficiently

create_iterator_classes(IntDictStrategy)

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
    iterator = w_data.iteritems()
    while 1:
        w_key, w_value = iterator.next_item()
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
    return W_DictMultiIterKeysObject(space, w_dict.iterkeys())

def eq__DictMulti_DictMulti(space, w_left, w_right):
    if space.is_w(w_left, w_right):
        return space.w_True

    if w_left.length() != w_right.length():
        return space.w_False
    iteratorimplementation = w_left.iteritems()
    while 1:
        w_key, w_val = iteratorimplementation.next_item()
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
    iteratorimplementation = w_a.iteritems()
    while 1:
        w_key, w_val = iteratorimplementation.next_item()
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
    return w_self.w_keys()

def dict_values__DictMulti(space, w_self):
    return space.newlist(w_self.values())

def dict_iteritems__DictMulti(space, w_self):
    return W_DictMultiIterItemsObject(space, w_self.iteritems())

def dict_iterkeys__DictMulti(space, w_self):
    return W_DictMultiIterKeysObject(space, w_self.iterkeys())

def dict_itervalues__DictMulti(space, w_self):
    return W_DictMultiIterValuesObject(space, w_self.itervalues())

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


class W_BaseDictMultiIterObject(W_Object):
    from pypy.objspace.std.dicttype import dictiter_typedef as typedef

    _immutable_fields_ = ["iteratorimplementation"]

    ignore_for_isinstance_cache = True

    def __init__(w_self, space, iteratorimplementation):
        w_self.space = space
        w_self.iteratorimplementation = iteratorimplementation

class W_DictMultiIterKeysObject(W_BaseDictMultiIterObject):
    pass

class W_DictMultiIterValuesObject(W_BaseDictMultiIterObject):
    pass

class W_DictMultiIterItemsObject(W_BaseDictMultiIterObject):
    pass

registerimplementation(W_DictMultiIterKeysObject)
registerimplementation(W_DictMultiIterValuesObject)
registerimplementation(W_DictMultiIterItemsObject)

def iter__DictMultiIterKeysObject(space, w_dictiter):
    return w_dictiter

def next__DictMultiIterKeysObject(space, w_dictiter):
    iteratorimplementation = w_dictiter.iteratorimplementation
    w_key = iteratorimplementation.next_key()
    if w_key is not None:
        return w_key
    raise OperationError(space.w_StopIteration, space.w_None)

def iter__DictMultiIterValuesObject(space, w_dictiter):
    return w_dictiter

def next__DictMultiIterValuesObject(space, w_dictiter):
    iteratorimplementation = w_dictiter.iteratorimplementation
    w_value = iteratorimplementation.next_value()
    if w_value is not None:
        return w_value
    raise OperationError(space.w_StopIteration, space.w_None)

def iter__DictMultiIterItemsObject(space, w_dictiter):
    return w_dictiter

def next__DictMultiIterItemsObject(space, w_dictiter):
    iteratorimplementation = w_dictiter.iteratorimplementation
    w_key, w_value = iteratorimplementation.next_item()
    if w_key is not None:
        return space.newtuple([w_key, w_value])
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
eq__DictViewKeys_frozensettypedef = eq__DictViewKeys_DictViewKeys

eq__DictViewKeys_DictViewItems = eq__DictViewKeys_DictViewKeys
eq__DictViewItems_DictViewItems = eq__DictViewKeys_DictViewKeys
eq__DictViewItems_settypedef = eq__DictViewItems_DictViewItems
eq__DictViewItems_frozensettypedef = eq__DictViewItems_DictViewItems

def repr__DictViewKeys(space, w_dictview):
    w_seq = space.call_function(space.w_list, w_dictview)
    w_repr = space.repr(w_seq)
    return space.wrap("%s(%s)" % (space.type(w_dictview).getname(space),
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
