from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef
from pypy.interpreter.error import OperationError

def descr__new__(space, w_longtype, w_value=None):
    from longobject import W_LongObject
    if w_value is None:
        w_obj = W_LongObject(space)
    else:
        w_obj = space.long(w_value)
    return space.w_long.check_user_subclass(w_longtype, w_obj)

# ____________________________________________________________

long_typedef = StdTypeDef("long", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
