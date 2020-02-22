from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef


class W_NoneObject(W_Root):
    def unwrap(self, space):
        return None

    def descr_nonzero(self, space):
        return space.w_False

    def descr_repr(self, space):
        return space.newtext('None')


W_NoneObject.w_None = W_NoneObject()

W_NoneObject.typedef = TypeDef("NoneType",
    __nonzero__ = interp2app(W_NoneObject.descr_nonzero),
    __repr__ = interp2app(W_NoneObject.descr_repr),
)
W_NoneObject.typedef.acceptable_as_base_class = False
