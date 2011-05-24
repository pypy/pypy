from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.dictmultiobject import W_DictMultiObject, IteratorImplementation
from pypy.objspace.std.typeobject import unwrap_cell
from pypy.interpreter.error import OperationError


class W_DictProxyObject(W_DictMultiObject):
    def __init__(w_self, space, w_type):
        W_DictMultiObject.__init__(w_self, space)
        w_self.w_type = w_type

    def impl_getitem(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.impl_getitem_str(space.str_w(w_lookup))
        else:
            return None

    def impl_getitem_str(self, lookup):
        return self.w_type.getdictvalue(self.space, lookup)

    def impl_setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            raise OperationError(space.w_TypeError, space.wrap("cannot add non-string keys to dict of a type"))

    def impl_setitem_str(self, name, w_value):
        try:
            self.w_type.setdictvalue(self.space, name, w_value)
        except OperationError, e:
            if not e.match(self.space, self.space.w_TypeError):
                raise
            w_type = self.w_type
            if not w_type.is_cpytype():
                raise
            # xxx obscure workaround: allow cpyext to write to type->tp_dict.
            # xxx like CPython, we assume that this is only done early after
            # xxx the type is created, and we don't invalidate any cache.
            w_type.dict_w[name] = w_value

    def impl_setdefault(self, w_key, w_default):
        space = self.space
        w_result = self.impl_getitem(w_key)
        if w_result is not None:
            return w_result
        self.impl_setitem(w_key, w_default)
        return w_default

    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            if not self.w_type.deldictvalue(space, w_key):
                raise KeyError
        else:
            raise KeyError

    def impl_length(self):
        return len(self.w_type.dict_w)

    def impl_iter(self):
        return DictProxyIteratorImplementation(self.space, self)

    def impl_keys(self):
        space = self.space
        return [space.wrap(key) for key in self.w_type.dict_w.iterkeys()]

    def impl_values(self):
        return [unwrap_cell(self.space, w_value) for w_value in self.w_type.dict_w.itervalues()]

    def impl_items(self):
        space = self.space
        return [space.newtuple([space.wrap(key), unwrap_cell(self.space, w_value)])
                    for (key, w_value) in self.w_type.dict_w.iteritems()]

    def impl_clear(self):
        self.w_type.dict_w.clear()
        self.w_type.mutated()

    def _as_rdict(self):
        assert 0, "should be unreachable"

    def _clear_fields(self):
        assert 0, "should be unreachable"

class DictProxyIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.w_type.dict_w.iteritems()

    def next_entry(self):
        for key, w_value in self.iterator:
            return (self.space.wrap(key), unwrap_cell(self.space, w_value))
        else:
            return (None, None)
