from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef


def descr__new__(space, w_tupletype, w_items=()):
    tuple_w = space.unpackiterable(w_items)
    w_obj = space.newtuple(tuple_w)
    return space.w_tuple.check_user_subclass(w_tupletype, w_obj)

# ____________________________________________________________

tuple_typedef = StdTypeDef("tuple", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
