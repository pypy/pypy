from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef


def descr__new__(space, w_tupletype, w_items=()):
    tuple_w = space.unpackiterable(w_items)
    return space.newtuple(tuple_w)

# ____________________________________________________________

tuple_typedef = StdTypeDef("tuple", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
