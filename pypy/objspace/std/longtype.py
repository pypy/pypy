from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.strutil import string_to_long
from pypy.interpreter.error import OperationError
from pypy.objspace.std.inttype import int_typedef

def descr__new__(space, w_longtype, w_value=None, w_base=None):
    from pypy.objspace.std.longobject import W_LongObject
    if w_base is None:
        # check for easy cases
        if w_value is None:
            value = 0L
        elif isinstance(w_value, W_LongObject):
            value = w_value.longval
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                value = string_to_long(space.unwrap(w_value))
            except ValueError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.args[0]))
        else:
            # otherwise, use the __long__() method
            w_obj = space.long(w_value)
            # 'long(x)' should return whatever x.__long__() returned
            if space.is_true(space.is_(w_longtype, space.w_long)):
                return w_obj
            value = space.unwrap(w_obj)
            if isinstance(value, int):    # XXX typechecking in unwrap!
                value = long(value)
            if not isinstance(value, long):
                raise OperationError(space.w_ValueError,
                                 space.wrap("value can't be converted to long"))
    else:
        base = space.unwrap(w_base)
        if not isinstance(base, int):   # XXX typechecking in unwrap!
            raise OperationError(space.w_TypeError,
                                 space.wrap("an integer is required"))
        s = space.unwrap(w_value)
        if not isinstance(s, str):   # XXX typechecking in unwrap!
            raise OperationError(space.w_TypeError,
                                 space.wrap("long() can't convert non-string "
                                            "with explicit base"))
        try:
            value = string_to_long(s, base)
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.args[0]))

    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    w_obj.__init__(space, value)
    return w_obj

# ____________________________________________________________

long_typedef = StdTypeDef("long",
    __new__ = newmethod(descr__new__),
    )
# hack to allow automatic int to long conversion: the int.__xyz__ methods
# will fall back to their long.__xyz__ counterparts if they fail
long_typedef.could_also_match = int_typedef
