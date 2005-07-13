from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.error import OperationError
from pypy.objspace.std.strutil import string_to_float, ParseStringError

def descr__new__(space, w_floattype, w_x=0.0):
    from pypy.objspace.std.floatobject import W_FloatObject
    w_value = w_x     # 'x' is the keyword argument name in CPython
    if space.is_true(space.isinstance(w_value, space.w_str)):
        strvalue = space.str_w(w_value)
        try:
            value = string_to_float(strvalue)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))
        except OverflowError, e:
            # this should not happen, but if it does, catch it!
            raise OperationError(space.w_OverflowError,
                                 space.wrap(str(e)))
    elif space.is_true(space.isinstance(w_value, space.w_unicode)):
        from unicodeobject import unicode_to_decimal_w
        strvalue = unicode_to_decimal_w(space, w_value)
        try:
            value = string_to_float(strvalue)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))
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
