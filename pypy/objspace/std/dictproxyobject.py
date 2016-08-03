# Read-only proxy for mappings. PyPy does not have a separate type for
# type.__dict__, so PyDictProxy_New has to use a custom read-only mapping.

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from pypy.interpreter.typedef import TypeDef, interp2app

class W_DictProxyObject(W_Root):
    "Read-only proxy for mappings."

    def __init__(self, w_mapping):
        self.w_mapping = w_mapping

    def descr_len(self, space):
        return space.len(self.w_mapping)

    def descr_getitem(self, space, w_key):
        return space.getitem(self.w_mapping, w_key)

    def descr_contains(self, space, w_key):
        return space.contains(self.w_mapping, w_key)

    def descr_iter(self, space):
        return space.iter(self.w_mapping)

    def descr_str(self, space):
        return space.str(self.w_mapping)

    def descr_repr(self, space):
        return space.repr(self.w_mapping)

    @unwrap_spec(w_default=WrappedDefault(None))
    def get_w(self, space, w_key, w_default):
        return space.call_method(self.w_mapping, "get", w_key, w_default)

    def keys_w(self, space):
        return space.call_method(self.w_mapping, "keys")

    def values_w(self, space):
        return space.call_method(self.w_mapping, "values")

    def items_w(self, space):
        return space.call_method(self.w_mapping, "items")

    def copy_w(self, space):
        return space.call_method(self.w_mapping, "copy")

W_DictProxyObject.typedef = TypeDef(
    'mappingproxy',
    __len__=interp2app(W_DictProxyObject.descr_len),
    __getitem__=interp2app(W_DictProxyObject.descr_getitem),
    __contains__=interp2app(W_DictProxyObject.descr_contains),
    __iter__=interp2app(W_DictProxyObject.descr_iter),
    __str__=interp2app(W_DictProxyObject.descr_str),
    __repr__=interp2app(W_DictProxyObject.descr_repr),
    get=interp2app(W_DictProxyObject.get_w),
    keys=interp2app(W_DictProxyObject.keys_w),
    values=interp2app(W_DictProxyObject.values_w),
    items=interp2app(W_DictProxyObject.items_w),
    copy=interp2app(W_DictProxyObject.copy_w)
)
