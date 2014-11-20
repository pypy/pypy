from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef


class W_NoneObject(W_Root):
    def unwrap(w_self, space):
        return None

    def descr_bool(self, space):
        return space.w_False

    def descr_repr(self, space):
        return space.wrap('None')


W_NoneObject.w_None = W_NoneObject()

W_NoneObject.typedef = TypeDef("NoneType",
    __bool__ = interp2app(W_NoneObject.descr_bool),
    __repr__ = interp2app(W_NoneObject.descr_repr),
)
W_NoneObject.typedef.acceptable_as_base_class = False
