from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef


class W_NoneObject(W_Root):
    def unwrap(self, space):
        return None

    @staticmethod
    def descr_new(space, w_type):
        "Create and return a new object.  See help(type) for accurate signature."
        return space.w_None

    def descr_bool(self, space):
        return space.w_False

    def descr_repr(self, space):
        return space.newtext('None')

    def descr_or(self, space, w_other):
        w_builtins = space.getbuiltinmodule('typing')
        w_union = space.getattr(w_builtins, space.newtext("Union"))
        w_getitem = space.getattr(w_union, space.newtext("__getitem__"))
        w_tuple = space.newtuple2(self, w_other)
        return space.call_function(w_getitem, w_tuple)


W_NoneObject.w_None = W_NoneObject()

W_NoneObject.typedef = TypeDef("NoneType",
    __new__ = interp2app(W_NoneObject.descr_new),
    __bool__ = interp2app(W_NoneObject.descr_bool),
    __repr__ = interp2app(W_NoneObject.descr_repr),
    __or__ = interp2app(W_NoneObject.descr_or),
)
W_NoneObject.typedef.acceptable_as_base_class = False
