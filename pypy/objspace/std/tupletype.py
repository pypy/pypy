from pypy.objspace.std.stdtypedef import *


def descr__new__(space, w_tupletype, w_items=None):
    from pypy.objspace.std.tupleobject import W_TupleObject
    if w_items is None:
        tuple_w = []
    else:
        tuple_w = space.unpackiterable(w_items)
    w_obj = space.allocate_instance(W_TupleObject, w_tupletype)
    w_obj.__init__(space, tuple_w)
    return w_obj

# ____________________________________________________________

tuple_typedef = StdTypeDef("tuple",
    __new__ = newmethod(descr__new__),
    )
