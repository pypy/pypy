from pypy.objspace.std.stdtypedef import *

def descr__new__(space, w_floattype, w_value=None):
    if w_value is None:
        w_obj = space.newfloat(0.0)
    else:
        if space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                w_obj = space.newfloat(float(space.unwrap(w_value)))
            except ValueError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(str(e)))
        else:
            w_obj = space.float(w_value)
    return space.w_float.build_user_subclass(w_floattype, w_obj)

# ____________________________________________________________

float_typedef = StdTypeDef("float",
    __new__ = newmethod(descr__new__),
    )
