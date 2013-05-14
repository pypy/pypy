from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.settype import set_typedef as settypedef
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.frozensettype import frozenset_typedef as frozensettypedef
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.signature import Signature

from rpython.rlib.objectmodel import r_dict, specialize, newlist_hint
from rpython.rlib.debug import mark_dict_non_null
from rpython.tool.sourcetools import func_with_new_name

from rpython.rlib import rerased, jit

UNROLL_CUTOFF = 5

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

@specialize.call_location()
def w_dict_unrolling_heuristic(w_dct):
    """ In which cases iterating over dict items can be unrolled.
    Note that w_dct is an instance of W_DictMultiObject, not necesarilly
    an actual dict
    """
    return jit.isvirtual(w_dct) or (jit.isconstant(w_dct) and
                                    w_dct.length() <= UNROLL_CUTOFF)


class W_DictMultiObject(W_Object):
    @staticmethod
    def allocate_and_init_instance(space, w_type=None, module=False,
                                   instance=False, strdict=False, kwargs=False):

        if space.config.objspace.std.withcelldict and module:
            from pypy.objspace.std.celldict import ModuleDictStrategy
            assert w_type is None
            # every module needs its own strategy, because the strategy stores
            # the version tag
            strategy = ModuleDictStrategy(space)
        elif space.config.objspace.std.withmapdict and instance:
            from pypy.objspace.std.mapdict import MapDictStrategy
            strategy = space.fromcache(MapDictStrategy)

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

    def setitem_str(self, key, w_value):
        self.strategy.setitem_str(self, key, w_value)

    def descr_init(self, space, __args__):
        init_or_update(space, self, __args__, 'dict')

    def descr_eq(self, space, w_other):
        if space.is_w(self, w_other):
            return space.w_True

        if self.length() != w_other.length():
            return space.w_False
        iteratorimplementation = self.iteritems()
        while 1:
            w_key, w_val = iteratorimplementation.next_item()
            if w_key is None:
                break
            w_rightval = w_other.getitem(w_key)
            if w_rightval is None:
                return space.w_False
            if not space.eq_w(w_val, w_rightval):
                return space.w_False
        return space.w_True

    def descr_ne(self, space, w_other):
        # XXX automatize this
        return space.not_(self.descr_eq(space, w_other))

    def descr_lt(self, space, w_other):
        # Different sizes, no problem
        if self.length() < w_other.length():
            return space.w_True
        if self.length() > w_other.length():
            return space.w_False

        # Same size
        w_leftdiff, w_leftval = characterize(space, self, w_other)
        if w_leftdiff is None:
            return space.w_False
        w_rightdiff, w_rightval = characterize(space, w_other, self)
        if w_rightdiff is None:
            # w_leftdiff is not None, w_rightdiff is None
            return space.w_True
        w_res = space.lt(w_leftdiff, w_rightdiff)
        if (not space.is_true(w_res) and
            space.eq_w(w_leftdiff, w_rightdiff) and
            w_rightval is not None):
            w_res = space.lt(w_leftval, w_rightval)
        return w_res

    def descr_len(self, space):
        return space.wrap(self.length())

    def descr_iter(self, space):
        return W_DictMultiIterKeysObject(space, self.iterkeys())

    def descr_contains(self, space, w_key):
        return space.newbool(self.getitem(w_key) is not None)

    def descr_getitem(self, space, w_key):
        w_value = self.getitem(w_key)
        if w_value is not None:
            return w_value

        w_missing_item = self.missing_method(space, w_key)
        if w_missing_item is not None:
            return w_missing_item

        space.raise_key_error(w_key)

    def descr_setitem(self, space, w_newkey, w_newvalue):
        self.setitem(w_newkey, w_newvalue)

    def descr_delitem(self, space, w_key):
        try:
            self.delitem(w_key)
        except KeyError:
            space.raise_key_error(w_key)

    def descr_reversed(self, space):
        raise OperationError(space.w_TypeError, space.wrap('argument to reversed() must be a sequence'))

    def descr_copy(self, space):
        """D.copy() -> a shallow copy of D"""
        w_new = W_DictMultiObject.allocate_and_init_instance(space)
        update1_dict_dict(space, w_new, self)
        return w_new

    def descr_items(self, space):
        """D.items() -> list of D's (key, value) pairs, as 2-tuples"""
        return space.newlist(self.items())

    def descr_keys(self, space):
        """D.keys() -> list of D's keys"""
        return self.w_keys()

    def descr_values(self, space):
        """D.values() -> list of D's values"""
        return space.newlist(self.values())

    def descr_iteritems(self, space):
        """D.iteritems() -> an iterator over the (key, value) items of D"""
        return W_DictMultiIterItemsObject(space, self.iteritems())

    def descr_iterkeys(self, space):
        """D.iterkeys() -> an iterator over the keys of D"""
        return W_DictMultiIterKeysObject(space, self.iterkeys())

    def descr_itervalues(self, space):
        """D.itervalues() -> an iterator over the values of D"""
        return W_DictMultiIterValuesObject(space, self.itervalues())

    def descr_viewitems(self, space):
        """D.viewitems() -> a set-like object providing a view on D's items"""
        return W_DictViewItemsObject(space, self)

    def descr_viewkeys(self, space):
        """D.viewkeys() -> a set-like object providing a view on D's keys"""
        return W_DictViewKeysObject(space, self)

    def descr_viewvalues(self, space):
        """D.viewvalues() -> an object providing a view on D's values"""
        return W_DictViewValuesObject(space, self)

    def descr_has_key(self, space, w_key):
        """D.has_key(k) -> True if D has a key k, else False"""
        # XXX duplication with contains
        return space.newbool(self.getitem(w_key) is not None)

    def descr_clear(self, space):
        """D.clear() -> None.  Remove all items from D."""
        self.clear()

    @gateway.unwrap_spec(w_default=gateway.WrappedDefault(None))
    def descr_get(self, space, w_key, w_default):
        """D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None."""
        w_value = self.getitem(w_key)
        if w_value is not None:
            return w_value
        else:
            return w_default

    @gateway.unwrap_spec(defaults_w='args_w')
    def descr_pop(self, space, w_key, defaults_w):
        """D.pop(k[,d]) -> v, remove specified key and return the
        corresponding value\nIf key is not found, d is returned if given,
        otherwise KeyError is raised
        """
        len_defaults = len(defaults_w)
        if len_defaults > 1:
            raise operationerrfmt(space.w_TypeError,
                                  "pop expected at most 2 arguments, got %d",
                                  1 + len_defaults)
        w_item = self.getitem(w_key)
        if w_item is None:
            if len_defaults > 0:
                return defaults_w[0]
            else:
                space.raise_key_error(w_key)
        else:
            self.delitem(w_key)
            return w_item

    def descr_popitem(self, space):
        """D.popitem() -> (k, v), remove and return some (key, value) pair as
        a\n2-tuple; but raise KeyError if D is empty"""
        try:
            w_key, w_value = self.popitem()
        except KeyError:
            raise OperationError(space.w_KeyError,
                                 space.wrap("popitem(): dictionary is empty"))
        return space.newtuple([w_key, w_value])

    @gateway.unwrap_spec(w_default=gateway.WrappedDefault(None))
    def descr_setdefault(self, space, w_key, w_default):
        """D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D"""
        return self.setdefault(w_key, w_default)

    def descr_update(self, space, __args__):
        """D.update(E, **F) -> None.  Update D from E and F: for k in E: D[k]
        = E[k]\n(if E has keys else: for (k, v) in E: D[k] = v) then: for k in
        F: D[k] = F[k]"""
        init_or_update(space, self, __args__, 'dict.update')


def _add_indirections():
    dict_methods = "getitem getitem_str setitem setdefault \
                    popitem delitem clear \
                    length w_keys values items \
                    iterkeys itervalues iteritems \
                    listview_str listview_unicode listview_int \
                    view_as_kwargs".split()

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

    def listview_unicode(self, w_dict):
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
        elif type(w_key) is self.space.UnicodeObjectCls:
            self.switch_to_unicode_strategy(w_dict)
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

    def switch_to_unicode_strategy(self, w_dict):
        strategy = self.space.fromcache(UnicodeDictStrategy)
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
        if self.dictimplementation is not None and self.len != -1:
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
        if self.is_correct_type(w_key):
            return self.unerase(w_dict.dstorage).setdefault(self.unwrap(w_key), w_default)
        else:
            self.switch_to_object_strategy(w_dict)
            return w_dict.setdefault(w_key, w_default)

    def delitem(self, w_dict, w_key):
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

    def setitem_str(self, w_dict, s, w_value):
        self.setitem(w_dict, self.space.wrap(s), w_value)

    def switch_to_object_strategy(self, w_dict):
        assert 0, "should be unreachable"

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


class UnicodeDictStrategy(AbstractTypedStrategy, DictStrategy):

    erase, unerase = rerased.new_erasing_pair("unicode")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def wrap(self, unwrapped):
        return self.space.wrap(unwrapped)

    def unwrap(self, wrapped):
        return self.space.unicode_w(wrapped)

    def is_correct_type(self, w_obj):
        space = self.space
        return space.is_w(space.type(w_obj), space.w_unicode)

    def get_empty_storage(self):
        res = {}
        mark_dict_non_null(res)
        return self.erase(res)

    def _never_equal_to(self, w_lookup_type):
        return _never_equal_to_string(self.space, w_lookup_type)

    # we should implement the same shortcuts as we do for StringDictStrategy

    ## def setitem_str(self, w_dict, key, w_value):
    ##     assert key is not None
    ##     self.unerase(w_dict.dstorage)[key] = w_value

    ## def getitem(self, w_dict, w_key):
    ##     space = self.space
    ##     # -- This is called extremely often.  Hack for performance --
    ##     if type(w_key) is space.StringObjectCls:
    ##         return self.getitem_str(w_dict, w_key.unwrap(space))
    ##     # -- End of performance hack --
    ##     return AbstractTypedStrategy.getitem(self, w_dict, w_key)

    ## def getitem_str(self, w_dict, key):
    ##     assert key is not None
    ##     return self.unerase(w_dict.dstorage).get(key, None)

    def listview_unicode(self, w_dict):
        return self.unerase(w_dict.dstorage).keys()

    ## def w_keys(self, w_dict):
    ##     return self.space.newlist_str(self.listview_str(w_dict))

    def wrapkey(space, key):
        return space.wrap(key)

    ## @jit.look_inside_iff(lambda self, w_dict:
    ##                      w_dict_unrolling_heuristic(w_dict))
    ## def view_as_kwargs(self, w_dict):
    ##     d = self.unerase(w_dict.dstorage)
    ##     l = len(d)
    ##     keys, values = [None] * l, [None] * l
    ##     i = 0
    ##     for key, val in d.iteritems():
    ##         keys[i] = key
    ##         values[i] = val
    ##         i += 1
    ##     return keys, values

create_iterator_classes(UnicodeDictStrategy)


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
        update1_pairs(space, w_dict, w_data)
    else:
        if isinstance(w_data, W_DictMultiObject):    # optimization case only
            update1_dict_dict(space, w_dict, w_data)
        else:
            # general case -- "for k in o.keys(): dict.__setitem__(d, k, o[k])"
            update1_keys(space, w_dict, w_data)


@jit.look_inside_iff(lambda space, w_dict, w_data:
                     w_dict_unrolling_heuristic(w_data))
def update1_dict_dict(space, w_dict, w_data):
    iterator = w_data.iteritems()
    while 1:
        w_key, w_value = iterator.next_item()
        if w_key is None:
            break
        w_dict.setitem(w_key, w_value)


def update1_pairs(space, w_dict, w_data):
    for w_pair in space.listview(w_data):
        pair = space.fixedview(w_pair)
        if len(pair) != 2:
            raise OperationError(space.w_ValueError,
                         space.wrap("sequence of pairs expected"))
        w_key, w_value = pair
        w_dict.setitem(w_key, w_value)


def update1_keys(space, w_dict, w_data):
    w_keys = space.call_method(w_data, "keys")
    for w_key in space.listview(w_keys):
        w_value = space.getitem(w_data, w_key)
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


# ____________________________________________________________
# Iteration


class W_BaseDictMultiIterObject(W_Object):
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

class W_DictViewItemsObject(W_DictViewObject):
    def descr__iter__(self, space):
        return W_DictMultiIterItemsObject(space, self.w_dict.iteritems())
registerimplementation(W_DictViewItemsObject)

class W_DictViewKeysObject(W_DictViewObject):
    def descr__iter__(self, space):
        return W_DictMultiIterKeysObject(space, self.w_dict.iterkeys())
registerimplementation(W_DictViewKeysObject)

class W_DictViewValuesObject(W_DictViewObject):
    def descr__iter__(self, space):
        return W_DictMultiIterValuesObject(space, self.w_dict.itervalues())
registerimplementation(W_DictViewValuesObject)

def len__DictViewKeys(space, w_dictview):
    return space.len(w_dictview.w_dict)
len__DictViewItems = len__DictViewValues = len__DictViewKeys

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


register_all(vars(), globals())

def descr_fromkeys(space, w_type, w_keys, w_fill=None):
    from pypy.objspace.std.dictmultiobject import W_DictMultiObject
    if w_fill is None:
        w_fill = space.w_None
    if space.is_w(w_type, space.w_dict):
        w_dict = W_DictMultiObject.allocate_and_init_instance(space, w_type)

        strlist = space.listview_str(w_keys)
        if strlist is not None:
            for key in strlist:
                w_dict.setitem_str(key, w_fill)
        else:
            for w_key in space.listview(w_keys):
                w_dict.setitem(w_key, w_fill)
    else:
        w_dict = space.call_function(w_type)
        for w_key in space.listview(w_keys):
            space.setitem(w_dict, w_key, w_fill)
    return w_dict


app = gateway.applevel('''
    def dictrepr(currently_in_repr, d):
        if len(d) == 0:
            return "{}"
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


def descr_repr(space, w_dict):
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return dictrepr(space, w_currently_in_repr, w_dict)


# ____________________________________________________________

def descr__new__(space, w_dicttype, __args__):
    from pypy.objspace.std.dictmultiobject import W_DictMultiObject
    w_obj = W_DictMultiObject.allocate_and_init_instance(space, w_dicttype)
    return w_obj

# ____________________________________________________________

W_DictMultiObject.typedef = StdTypeDef("dict",
    __doc__ = '''dict() -> new empty dictionary.
dict(mapping) -> new dictionary initialized from a mapping object\'s
    (key, value) pairs.
dict(seq) -> new dictionary initialized as if via:
    d = {}
    for k, v in seq:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)''',
    __new__ = gateway.interp2app(descr__new__),
    __hash__ = None,
    __repr__ = gateway.interp2app(descr_repr),
    __init__ = gateway.interp2app(W_DictMultiObject.descr_init),

    __eq__ = gateway.interp2app(W_DictMultiObject.descr_eq),
    __ne__ = gateway.interp2app(W_DictMultiObject.descr_ne),
    __lt__ = gateway.interp2app(W_DictMultiObject.descr_lt),
    # XXX other comparison methods?

    __len__ = gateway.interp2app(W_DictMultiObject.descr_len),
    __iter__ = gateway.interp2app(W_DictMultiObject.descr_iter),
    __contains__ = gateway.interp2app(W_DictMultiObject.descr_contains),

    __getitem__ = gateway.interp2app(W_DictMultiObject.descr_getitem),
    __setitem__ = gateway.interp2app(W_DictMultiObject.descr_setitem),
    __delitem__ = gateway.interp2app(W_DictMultiObject.descr_delitem),

    __reversed__ = gateway.interp2app(W_DictMultiObject.descr_reversed),
    fromkeys = gateway.interp2app(descr_fromkeys, as_classmethod=True),
    copy = gateway.interp2app(W_DictMultiObject.descr_copy),
    items = gateway.interp2app(W_DictMultiObject.descr_items),
    keys = gateway.interp2app(W_DictMultiObject.descr_keys),
    values = gateway.interp2app(W_DictMultiObject.descr_values),
    iteritems = gateway.interp2app(W_DictMultiObject.descr_iteritems),
    iterkeys = gateway.interp2app(W_DictMultiObject.descr_iterkeys),
    itervalues = gateway.interp2app(W_DictMultiObject.descr_itervalues),
    viewkeys = gateway.interp2app(W_DictMultiObject.descr_viewkeys),
    viewitems = gateway.interp2app(W_DictMultiObject.descr_viewitems),
    viewvalues = gateway.interp2app(W_DictMultiObject.descr_viewvalues),
    has_key = gateway.interp2app(W_DictMultiObject.descr_has_key),
    clear = gateway.interp2app(W_DictMultiObject.descr_clear),
    get = gateway.interp2app(W_DictMultiObject.descr_get),
    pop = gateway.interp2app(W_DictMultiObject.descr_pop),
    popitem = gateway.interp2app(W_DictMultiObject.descr_popitem),
    setdefault = gateway.interp2app(W_DictMultiObject.descr_setdefault),
    update = gateway.interp2app(W_DictMultiObject.descr_update),
    )
W_DictMultiObject.typedef.registermethods(globals())
dict_typedef = W_DictMultiObject.typedef

# ____________________________________________________________

def descr_dictiter__length_hint__(space, w_self):
    from pypy.objspace.std.dictmultiobject import W_BaseDictMultiIterObject
    assert isinstance(w_self, W_BaseDictMultiIterObject)
    return space.wrap(w_self.iteratorimplementation.length())


def descr_dictiter__reduce__(w_self, space):
    """
    This is a slightly special case of pickling.
    Since iteration over a dict is a bit hairy,
    we do the following:
    - create a clone of the dict iterator
    - run it to the original position
    - collect all remaining elements into a list
    At unpickling time, we just use that list
    and create an iterator on it.
    This is of course not the standard way.

    XXX to do: remove this __reduce__ method and do
    a registration with copy_reg, instead.
    """
    w_mod    = space.getbuiltinmodule('_pickle_support')
    mod      = space.interp_w(MixedModule, w_mod)
    new_inst = mod.get('dictiter_surrogate_new')
    w_typeobj = space.gettypeobject(dictiter_typedef)

    raise OperationError(
        space.w_TypeError,
        space.wrap("can't pickle dictionary-keyiterator objects"))
    # XXXXXX get that working again

    # we cannot call __init__ since we don't have the original dict
    if isinstance(w_self, W_DictIter_Keys):
        w_clone = space.allocate_instance(W_DictIter_Keys, w_typeobj)
    elif isinstance(w_self, W_DictIter_Values):
        w_clone = space.allocate_instance(W_DictIter_Values, w_typeobj)
    elif isinstance(w_self, W_DictIter_Items):
        w_clone = space.allocate_instance(W_DictIter_Items, w_typeobj)
    else:
        msg = "unsupported dictiter type '%s' during pickling" % (w_self, )
        raise OperationError(space.w_TypeError, space.wrap(msg))
    w_clone.space = space
    w_clone.content = w_self.content
    w_clone.len = w_self.len
    w_clone.pos = 0
    w_clone.setup_iterator()
    # spool until we have the same pos
    while w_clone.pos < w_self.pos:
        w_obj = w_clone.next_entry()
        w_clone.pos += 1
    stuff = [w_clone.next_entry() for i in range(w_clone.pos, w_clone.len)]
    w_res = space.newlist(stuff)
    tup      = [
        w_res
    ]
    w_ret = space.newtuple([new_inst, space.newtuple(tup)])
    return w_ret

# ____________________________________________________________


W_BaseDictMultiIterObject.typedef = StdTypeDef("dictionaryiterator",
    __length_hint__ = gateway.interp2app(descr_dictiter__length_hint__),
    __reduce__      = gateway.interp2app(descr_dictiter__reduce__),
    )

# ____________________________________________________________
# Dict views

W_DictViewItemsObject.typedef = StdTypeDef(
    "dict_items",
    __iter__ = gateway.interp2app(W_DictViewItemsObject.descr__iter__)
    )

W_DictViewKeysObject.typedef = StdTypeDef(
    "dict_keys",
    __iter__ = gateway.interp2app(W_DictViewKeysObject.descr__iter__)
    )

W_DictViewValuesObject.typedef = StdTypeDef(
    "dict_values",
    __iter__ = gateway.interp2app(W_DictViewValuesObject.descr__iter__)
    )
