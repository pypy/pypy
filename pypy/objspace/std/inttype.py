from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef


def descr__new__(space, w_inttype, w_value=0, w_base=None):
    from intobject import W_IntObject
    if w_base == space.w_None:
        return space.int(w_value)
    else:
        # XXX write the logic for int("str", base)
        s = space.unwrap(w_value)
        base = space.unwrap(w_base)
        try:
            value = int(s, base)
        except TypeError, e:
            raise OperationError(space.w_TypeError,
                         space.wrap(str(e)))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                         space.wrap(str(e)))
        except OverflowError, e:
            raise OperationError(space.w_OverflowError,
                         space.wrap(str(e)))
        return W_IntObject(value)

# ____________________________________________________________

int_typedef = StdTypeDef("int", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
