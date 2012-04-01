from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.dictmultiobject import W_DictMultiObject, IteratorImplementation
from pypy.objspace.std.dictmultiobject import DictStrategy
from pypy.objspace.std.typeobject import unwrap_cell
from pypy.interpreter.error import OperationError, operationerrfmt

from pypy.rlib import rerased


class DictProxyStrategy(DictStrategy):

    erase, unerase = rerased.new_erasing_pair("dictproxy")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def __init__(w_self, space):
        DictStrategy.__init__(w_self, space)

    def getitem(self, w_dict, w_key):
        space = self.space
        w_lookup_type = space.type(w_key)
        if (space.is_w(w_lookup_type, space.w_str) or  # Most common path first
            space.abstract_issubclass_w(w_lookup_type, space.w_str)):
            return self.getitem_str(w_dict, space.str_w(w_key))
        elif space.abstract_issubclass_w(w_lookup_type, space.w_unicode):
            try:
                w_key = space.str(w_key)
            except OperationError, e:
                if not e.match(space, space.w_UnicodeEncodeError):
                    raise
                # non-ascii unicode is never equal to a byte string
                return None
            return self.getitem_str(w_dict, space.str_w(w_key))
        else:
            return None

    def getitem_str(self, w_dict, key):
        return self.unerase(w_dict.dstorage).getdictvalue(self.space, key)

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.setitem_str(w_dict, self.space.str_w(w_key), w_value)
        else:
            raise OperationError(space.w_TypeError, space.wrap("cannot add non-string keys to dict of a type"))

    def setitem_str(self, w_dict, key, w_value):
        w_type = self.unerase(w_dict.dstorage)
        try:
            w_type.setdictvalue(self.space, key, w_value)
        except OperationError, e:
            if not e.match(self.space, self.space.w_TypeError):
                raise
            if not w_type.is_cpytype():
                raise
            # xxx obscure workaround: allow cpyext to write to type->tp_dict
            # xxx even in the case of a builtin type.
            # xxx like CPython, we assume that this is only done early after
            # xxx the type is created, and we don't invalidate any cache.
            w_type.dict_w[key] = w_value

    def setdefault(self, w_dict, w_key, w_default):
        space = self.space
        w_result = self.getitem(w_dict, w_key)
        if w_result is not None:
            return w_result
        self.setitem(w_dict, w_key, w_default)
        return w_default

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = self.space.str_w(w_key)
            if not self.unerase(w_dict.dstorage).deldictvalue(space, key):
                raise KeyError
        else:
            raise KeyError

    def length(self, w_dict):
        return len(self.unerase(w_dict.dstorage).dict_w)

    def iter(self, w_dict):
        return DictProxyIteratorImplementation(self.space, self, w_dict)

    def keys(self, w_dict):
        space = self.space
        return space.newlist_str(self.unerase(w_dict.dstorage).dict_w.keys())

    def values(self, w_dict):
        return [unwrap_cell(self.space, w_value) for w_value in self.unerase(w_dict.dstorage).dict_w.itervalues()]

    def items(self, w_dict):
        space = self.space
        return [space.newtuple([space.wrap(key), unwrap_cell(self.space, w_value)])
                    for (key, w_value) in self.unerase(w_dict.dstorage).dict_w.iteritems()]

    def clear(self, w_dict):
        space = self.space
        w_type = self.unerase(w_dict.dstorage)
        if (not space.config.objspace.std.mutable_builtintypes
                and not w_type.is_heaptype()):
            msg = "can't clear dictionary of type '%s'"
            raise operationerrfmt(space.w_TypeError, msg, w_type.name)
        w_type.dict_w.clear()
        w_type.mutated(None)

class DictProxyIteratorImplementation(IteratorImplementation):
    def __init__(self, space, strategy, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        w_type = strategy.unerase(dictimplementation.dstorage)
        self.iterator = w_type.dict_w.iteritems()

    def next_entry(self):
        for key, w_value in self.iterator:
            return (self.space.wrap(key), unwrap_cell(self.space, w_value))
        else:
            return (None, None)
