from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef

def descr__new__(space, w_floattype, w_value=0):
    if space.is_true(space.isinstance(w_value, space.w_str)):
        try:
            w_obj = space.newfloat(float(space.unwrap(w_value)))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(str(e)))
    else:
        w_obj = space.float(w_value)
    return space.w_float.check_user_subclass(w_floattype, w_obj)

# ____________________________________________________________

float_typedef = StdTypeDef("float", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
