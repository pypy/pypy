from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.strutil import string_to_int
from pypy.interpreter.error import OperationError

def descr__new__(space, w_inttype, w_value=None, w_base=None):
    from pypy.objspace.std.intobject import W_IntObject
    if w_base is None:
        # check for easy cases
        if w_value is None:
            value = 0
        elif isinstance(w_value, W_IntObject):
            value = w_value.intval
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                value = string_to_int(space.unwrap(w_value))
            except ValueError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.args[0]))
        else:
            # otherwise, use the __int__() method
            w_obj = space.int(w_value)
            # 'int(x)' should return whatever x.__int__() returned
            if space.is_true(space.is_(w_inttype, space.w_int)):
                return w_obj
            value = space.unwrap(w_obj)
            if not isinstance(value, int):   # XXX typechecking in unwrap!
                raise OperationError(space.w_ValueError,
                                 space.wrap("value can't be converted to int"))
    else:
        base = space.unwrap(w_base)
        if not isinstance(base, int):   # XXX typechecking in unwrap!
            raise OperationError(space.w_TypeError,
                                 space.wrap("an integer is required"))
        s = space.unwrap(w_value)
        if not isinstance(s, str):   # XXX typechecking in unwrap!
            raise OperationError(space.w_TypeError,
                                 space.wrap("int() can't convert non-string "
                                            "with explicit base"))
        try:
            value = string_to_int(s, base)
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.args[0]))

    if isinstance(value, long):
        # XXX is this right??
        from pypy.objspace.std.longobject import W_LongObject
        w_obj = space.allocate_instance(W_LongObject, space.w_long)
        w_obj.__init__(space, value)
        return w_obj
    else:
        w_obj = space.allocate_instance(W_IntObject, w_inttype)
        w_obj.__init__(space, value)
        return w_obj

# ____________________________________________________________

int_typedef = StdTypeDef("int",
    __new__ = newmethod(descr__new__),
    )
