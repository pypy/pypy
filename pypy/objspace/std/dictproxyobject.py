from rpython.rlib import rerased
from rpython.rlib.objectmodel import iteritems_with_hash

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.dictmultiobject import (
    DictStrategy, W_DictObject, create_iterator_classes)
from pypy.objspace.std.typeobject import unwrap_cell


class W_DictProxyObject(W_DictObject):
    @staticmethod
    def descr_new(space, w_type, w_mapping):
        if (not space.lookup(w_mapping, "__getitem__") or
            space.isinstance_w(w_mapping, space.w_list) or
            space.isinstance_w(w_mapping, space.w_tuple)):
            raise oefmt(space.w_TypeError,
                        "mappingproxy() argument must be a mapping, not %T", w_mapping)
        strategy = space.fromcache(MappingProxyStrategy)
        storage = strategy.erase(w_mapping)
        w_obj = space.allocate_instance(W_DictProxyObject, w_type)
        W_DictProxyObject.__init__(w_obj, space, strategy, storage)
        return w_obj

    def descr_init(self, space, __args__):
        pass

    def descr_repr(self, space):
        return space.wrap(u"mappingproxy(%s)" % (
            space.unicode_w(W_DictObject.descr_repr(self, space))))

W_DictProxyObject.typedef = TypeDef(
    "mappingproxy", W_DictObject.typedef,
    __new__ = interp2app(W_DictProxyObject.descr_new),
    __init__ = interp2app(W_DictProxyObject.descr_init),
    __repr__ = interp2app(W_DictProxyObject.descr_repr),
)


class DictProxyStrategy(DictStrategy):
    """Exposes a W_TypeObject.dict_w at app-level.

    Uses getdictvalue() and setdictvalue() to access items.
    """
    erase, unerase = rerased.new_erasing_pair("dictproxy")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def getitem(self, w_dict, w_key):
        space = self.space
        w_lookup_type = space.type(w_key)
        if space.is_true(space.issubtype(w_lookup_type, space.w_unicode)):
            return self.getitem_str(w_dict, space.str_w(w_key))
        else:
            return None

    def getitem_str(self, w_dict, key):
        return self.unerase(w_dict.dstorage).getdictvalue(self.space, key)

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_unicode):
            self.setitem_str(w_dict, self.space.str_w(w_key), w_value)
        else:
            raise oefmt(space.w_TypeError,
                        "cannot add non-string keys to dict of a type")

    def setitem_str(self, w_dict, key, w_value):
        w_type = self.unerase(w_dict.dstorage)
        try:
            w_type.setdictvalue(self.space, key, w_value)
        except OperationError as e:
            if not e.match(self.space, self.space.w_TypeError):
                raise
            if not w_type.is_cpytype():
                raise
            # Allow cpyext to write to type->tp_dict even in the case
            # of a builtin type.
            # Like CPython, we assume that this is only done early
            # after the type is created, and we don't invalidate any
            # cache.  User code shoud call PyType_Modified().
            w_type.dict_w[key] = w_value

    def setdefault(self, w_dict, w_key, w_default):
        w_result = self.getitem(w_dict, w_key)
        if w_result is not None:
            return w_result
        self.setitem(w_dict, w_key, w_default)
        return w_default

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_unicode):
            key = self.space.str_w(w_key)
            if not self.unerase(w_dict.dstorage).deldictvalue(space, key):
                raise KeyError
        else:
            raise KeyError

    def length(self, w_dict):
        return len(self.unerase(w_dict.dstorage).dict_w)

    def w_keys(self, w_dict):
        space = self.space
        w_type = self.unerase(w_dict.dstorage)
        return space.newlist([_wrapkey(space, key)
                              for key in w_type.dict_w.iterkeys()])

    def values(self, w_dict):
        return [unwrap_cell(self.space, w_value) for w_value in self.unerase(w_dict.dstorage).dict_w.itervalues()]

    def items(self, w_dict):
        space = self.space
        w_type = self.unerase(w_dict.dstorage)
        return [space.newtuple([_wrapkey(space, key),
                                unwrap_cell(space, w_value)])
                for (key, w_value) in w_type.dict_w.iteritems()]

    def clear(self, w_dict):
        space = self.space
        w_type = self.unerase(w_dict.dstorage)
        if not w_type.is_heaptype():
            raise oefmt(space.w_TypeError,
                        "can't clear dictionary of type '%N'", w_type)
        w_type.dict_w.clear()
        w_type.mutated(None)

    def getiterkeys(self, w_dict):
        return self.unerase(w_dict.dstorage).dict_w.iterkeys()
    def getitervalues(self, w_dict):
        return self.unerase(w_dict.dstorage).dict_w.itervalues()
    def getiteritems_with_hash(self, w_dict):
        return iteritems_with_hash(self.unerase(w_dict.dstorage).dict_w)
    def wrapkey(space, key):
        return _wrapkey(space, key)
    def wrapvalue(space, value):
        return unwrap_cell(space, value)

def _wrapkey(space, key):
    # keys are utf-8 encoded identifiers from type's dict_w
    return space.wrap(key.decode('utf-8'))

create_iterator_classes(DictProxyStrategy)


class MappingProxyStrategy(DictStrategy):
    """Wraps an applevel mapping in a read-only dictionary."""
    erase, unerase = rerased.new_erasing_pair("mappingproxy")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def getitem(self, w_dict, w_key):
        try:
            return self.space.getitem(self.unerase(w_dict.dstorage), w_key)
        except OperationError as e:
            if not e.match(self.space, self.space.w_KeyError):
                raise
            return None

    def setitem(self, w_dict, w_key, w_value):
        raise oefmt(self.space.w_TypeError,
                    "'%T' object does not support item assignment", w_dict)

    def delitem(self, w_dict, w_key):
        raise oefmt(self.space.w_TypeError,
                    "'%T' object does not support item deletion", w_dict)

    def length(self, w_dict):
        return self.space.len_w(self.unerase(w_dict.dstorage))

    def getiterkeys(self, w_dict):
        return self.space.iter(
            self.space.call_method(self.unerase(w_dict.dstorage), "keys"))

    def getitervalues(self, w_dict):
        return self.space.iter(
            self.space.call_method(self.unerase(w_dict.dstorage), "values"))

    def getiteritems_with_hash(self, w_dict):
        return self.space.iter(
            self.space.call_method(self.unerase(w_dict.dstorage), "items"))

    @staticmethod
    def override_next_key(iterkeys):
        w_keys = iterkeys.iterator
        return iterkeys.space.next(w_keys)

    @staticmethod
    def override_next_value(itervalues):
        w_values = itervalues.iterator
        return itervalues.space.next(w_values)

    @staticmethod
    def override_next_item(iteritems):
        w_items = iteritems.iterator
        w_item = iteritems.space.next(w_items)
        w_key, w_value = iteritems.space.unpackiterable(w_item, 2)
        return w_key, w_value

    def clear(self, w_dict):
        raise oefmt(self.space.w_AttributeError, "clear")

    def copy(self, w_dict):
        return self.space.call_method(self.unerase(w_dict.dstorage), "copy")

create_iterator_classes(
    MappingProxyStrategy,
    override_next_key=MappingProxyStrategy.override_next_key,
    override_next_value=MappingProxyStrategy.override_next_value,
    override_next_item=MappingProxyStrategy.override_next_item)
