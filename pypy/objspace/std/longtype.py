from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.error import OperationError
from pypy.objspace.std.inttype import int_typedef

def descr__new__(space, w_longtype, w_value=None, w_base=None):
    from pypy.objspace.std.longobject import W_LongObject
    if w_base is None:
        w_base = space.w_None
    if w_value is None:
        value = 0L
    elif w_base == space.w_None and not space.is_true(space.isinstance(w_value, space.w_str)):
        w_obj = space.long(w_value)
        if space.is_true(space.is_(w_longtype, space.w_long)):
            return w_obj  # 'long(x)' should return
                          # whatever x.__long__() returned
        value = space.unwrap(w_obj)
        if isinstance(value, int):     # XXX typechecking in unwrap!
            value = long(value)
        if not isinstance(value, long):   # XXX typechecking in unwrap!
            raise OperationError(space.w_ValueError,
                             space.wrap("value can't be converted to long"))

    else:
        if w_base == space.w_None:
            base = -909 # don't blame us!!
        else:
            base = space.unwrap(w_base)
        s = space.unwrap(w_value)            
        try:
            value = long(s, base)
        except TypeError, e:
            raise OperationError(space.w_TypeError,
                         space.wrap(str(e)))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                         space.wrap(str(e)))
        except OverflowError, e:
            raise OperationError(space.w_OverflowError,
                         space.wrap(str(e)))
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
