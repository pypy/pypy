from pypy.objspace.std.stdtypedef import *

def descr__new__(space, w_longtype, w_value=None):
    from pypy.objspace.std.longobject import W_LongObject
    if w_value is None:
        value = 0L
    elif space.is_true(space.isinstance(w_value, space.w_str)):
        # XXX implement long("str", base)
        try:
            value = long(space.unwrap(w_value))
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(str(e)))
    else:
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
    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    w_obj.__init__(space, value)
    return w_obj

# ____________________________________________________________

long_typedef = StdTypeDef("long",
    __new__ = newmethod(descr__new__),
    )
