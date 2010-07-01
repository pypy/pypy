from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.strutil import ParseStringError
from pypy.objspace.std.strutil import interp_string_to_float

def descr__new__(space, w_floattype, w_x=0.0):
    from pypy.objspace.std.floatobject import W_FloatObject
    w_value = w_x     # 'x' is the keyword argument name in CPython
    if space.is_true(space.isinstance(w_value, space.w_str)):
        strvalue = space.str_w(w_value)
        try:
            value = interp_string_to_float(space, strvalue)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))
    elif space.is_true(space.isinstance(w_value, space.w_unicode)):
        if space.config.objspace.std.withropeunicode:
            from pypy.objspace.std.ropeunicodeobject import unicode_to_decimal_w
        else:
            from unicodeobject import unicode_to_decimal_w
        strvalue = unicode_to_decimal_w(space, w_value)
        try:
            value = interp_string_to_float(space, strvalue)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))
    else:
        w_obj = space.float(w_value)
        if space.is_w(w_floattype, space.w_float):
            return w_obj  # 'float(x)' should return
                          # whatever x.__float__() returned
        value = space.float_w(w_obj)
    w_obj = space.allocate_instance(W_FloatObject, w_floattype)
    W_FloatObject.__init__(w_obj, value)
    return w_obj


_float_format = float.__getformat__("float")
_double_format = float.__getformat__("double")
def descr___getformat__(space, w_cls, kind):
    if kind == "float":
        return space.wrap(_float_format)
    elif kind == "double":
        return space.wrap(_double_format)
    raise OperationError(space.w_ValueError,
                         space.wrap("only float and double are valid"))


# ____________________________________________________________

float_typedef = StdTypeDef("float",
    __doc__ = '''float(x) -> floating point number

Convert a string or number to a floating point number, if possible.''',
    __new__ = gateway.interp2app(descr__new__),
    __getformat__ = gateway.interp2app(descr___getformat__,
                                       unwrap_spec=[ObjSpace, W_Root, str],
                                       as_classmethod=True),
    )
