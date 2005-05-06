from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.error import OperationError

def descr__new__(space, w_floattype, w_value=0.0):
    from pypy.objspace.std.floatobject import W_FloatObject
    if space.is_true(space.isinstance(w_value, space.w_str)):
        try:
            value = float(space.str_w(w_value))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(str(e)))
    else:
        w_obj = space.float(w_value)
        if space.is_true(space.is_(w_floattype, space.w_float)):
            return w_obj  # 'float(x)' should return
                          # whatever x.__float__() returned
        value = space.float_w(w_obj)
    w_obj = space.allocate_instance(W_FloatObject, w_floattype)
    W_FloatObject.__init__(w_obj, space, value)
    return w_obj

# ____________________________________________________________

float_typedef = StdTypeDef("float",
    __new__ = newmethod(descr__new__),
    )
