from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef

def descr__new__(space, w_floattype, w_value=0):
    if space.is_true(space.isinstance(w_value, space.w_str)):
        try:
            return space.newfloat(float(space.unwrap(w_value)))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(str(e)))
    else:
        return space.float(w_value)

# ____________________________________________________________

float_typedef = StdTypeDef("float", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
