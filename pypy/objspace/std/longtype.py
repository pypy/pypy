from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.strutil import string_to_long
from pypy.interpreter.error import OperationError
from pypy.objspace.std.inttype import int_typedef
from pypy.interpreter.gateway import NoneNotWrapped

def descr__new__(space, w_longtype, w_value=0, w_base=NoneNotWrapped):
    from pypy.objspace.std.longobject import W_LongObject
    if w_base is None:
        # check for easy cases
        if isinstance(w_value, W_LongObject):
            value = w_value.longval
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                # XXX value can be unwrapped long
                value = string_to_long(space.str_w(w_value))
            except ValueError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.args[0]))
        else:
            # otherwise, use the __long__() method
            w_obj = space.long(w_value)
            # 'long(x)' should return whatever x.__long__() returned
            if space.is_true(space.is_(w_longtype, space.w_long)):
                return w_obj
            value = space.unwrap(w_obj) # XXX value can be unwrapped long
            if isinstance(value, int):    # XXX typechecking in unwrap!
                value = long(value)
            if not isinstance(value, long):
                raise OperationError(space.w_ValueError,
                                 space.wrap("value can't be converted to long"))
    else:
        base = space.int_w(w_base)

        if space.is_true(space.isinstance(w_value, space.w_unicode)):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError, e:
                raise OperationError(space.w_TypeError,
                                     space.wrap("long() can't convert non-string "
                                                "with explicit base"))
        try:
            # XXX value can be unwrapped long
            value = string_to_long(s, base)
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.args[0]))

    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    w_obj.__init__(space, value)
    return w_obj

def descr__getnewargs__(space, w_obj):
    from pypy.objspace.std.longobject import W_LongObject
    return space.newtuple([W_LongObject(space, w_obj.longval)])

# ____________________________________________________________

long_typedef = StdTypeDef("long",
    __new__ = newmethod(descr__new__),
    __getnewargs__ = newmethod(descr__getnewargs__),
    )
# hack to allow automatic int to long conversion: the int.__xyz__ methods
# will fall back to their long.__xyz__ counterparts if they fail
long_typedef.could_also_match = int_typedef
