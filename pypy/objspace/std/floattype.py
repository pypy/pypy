from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.error import OperationError

def descr__new__(space, w_floattype, w_value=None):
    from pypy.objspace.std.floatobject import W_FloatObject
    if w_value is None:
        value = 0.0
    elif space.is_true(space.isinstance(w_value, space.w_str)):
        try:
            value = float(space.unwrap(w_value))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(str(e)))
    else:
        w_obj = space.float(w_value)
        if space.is_true(space.is_(w_floattype, space.w_float)):
            return w_obj  # 'float(x)' should return
                          # whatever x.__float__() returned
        value = space.unwrap(w_obj)
        if isinstance(value, int):     # XXX typechecking in unwrap!
            value = float(value)
        if not isinstance(value, float):   # XXX typechecking in unwrap!
            raise OperationError(space.w_ValueError,
                             space.wrap("value can't be converted to float"))
    w_obj = space.allocate_instance(W_FloatObject, w_floattype)
    w_obj.__init__(space, value)
    return w_obj

# ____________________________________________________________

float_typedef = StdTypeDef("float",
    __new__ = newmethod(descr__new__),
    )
