from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.gateway import NoneNotWrapped

def descr__new__(space, w_tupletype, w_items=NoneNotWrapped):
    from pypy.objspace.std.tupleobject import W_TupleObject
    if w_items is None:
        tuple_w = []
    elif (space.is_w(w_tupletype, space.w_tuple) and
          space.is_w(space.type(w_items), space.w_tuple)):
        return w_items
    else:
        tuple_w = space.unpackiterable(w_items)
    w_obj = space.allocate_instance(W_TupleObject, w_tupletype)
    w_obj.__init__(space, tuple_w)
    return w_obj

def descr__getnewargs__(space, w_obj):
    from pypy.objspace.std.tupleobject import W_TupleObject
    return space.newtuple([W_TupleObject(space, w_obj.wrappeditems)])

# ____________________________________________________________

tuple_typedef = StdTypeDef("tuple",
    __new__ = newmethod(descr__new__),
    __getnewargs__ = newmethod(descr__getnewargs__),
    )
