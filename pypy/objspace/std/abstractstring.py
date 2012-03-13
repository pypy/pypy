from pypy.objspace.std.model import W_Object
from pypy.rlib.objectmodel import specialize


class W_AbstractBaseStringObject(W_Object):
    __slots__ = ()

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self.raw_value())

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractBaseStringObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return self.unwrap(space) is w_other.unwrap(space)

    def immutable_unique_id(w_self, space):
        if w_self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(w_self.unwrap(space)))

    def raw_value(w_self):
        raise NotImplemented("method not implemented")

    def unwrap(w_self, space):
        raise NotImplemented("method not implemented")

    def str_w(w_self, space):
        raise NotImplemented("method not implemented")

    def unicode_w(w_self, space):
        raise NotImplemented("method not implemented")


@specialize.arg(2)
def is_generic(space, w_self, fun):
    v = w_self._value
    if len(v) == 0:
        return space.w_False
    if len(v) == 1:
        return space.newbool(fun(v[0]))
    for idx in range(len(v)):
        if not fun(v[idx]):
            return space.w_False
    return space.w_True
