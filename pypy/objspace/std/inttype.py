from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.error import OperationError

def descr__new__(space, w_inttype, w_value=None, w_base=None):
    from pypy.objspace.std.intobject import W_IntObject
    if w_base is None:
        w_base = space.w_None
    if w_value is None:
        value = 0
    elif w_base == space.w_None and not space.is_true(space.isinstance(w_value, space.w_str)):
        w_obj = space.int(w_value)
        if space.is_true(space.is_(w_inttype, space.w_int)):
            return w_obj  # 'int(x)' should return whatever x.__int__() returned
        value = space.unwrap(w_obj)
        if not isinstance(value, int):   # XXX typechecking in unwrap!
            raise OperationError(space.w_ValueError,
                                 space.wrap("value can't be converted to int"))
    else:
        if w_base == space.w_None:
            base = -909 # don't blame us!!
        else:
            base = space.unwrap(w_base)
        # XXX write the logic for int("str", base)
        s = space.unwrap(w_value)
        try:
            value = int(s, base)
        except TypeError, e:
            raise OperationError(space.w_TypeError,
                         space.wrap(str(e)))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                         space.wrap(str(e)))
        except OverflowError, e:
            raise OperationError(space.w_OverflowError,
                         space.wrap(str(e)))
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
