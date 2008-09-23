from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.gateway import NoneNotWrapped

def wraptuple(space, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject
    return W_TupleObject(list_w)

def descr__new__(space, w_tupletype, w_sequence=NoneNotWrapped):
    from pypy.objspace.std.tupleobject import W_TupleObject
    if w_sequence is None:
        tuple_w = []
    elif (space.is_w(w_tupletype, space.w_tuple) and
          space.is_w(space.type(w_sequence), space.w_tuple)):
        return w_sequence
    else:
        tuple_w = space.viewiterable(w_sequence)
    w_obj = space.allocate_instance(space.TupleObjectCls, w_tupletype)
    space.TupleObjectCls.__init__(w_obj, tuple_w)
    return w_obj

# ____________________________________________________________

tuple_typedef = StdTypeDef("tuple",
    __doc__ = '''tuple() -> an empty tuple
tuple(sequence) -> tuple initialized from sequence's items

If the argument is a tuple, the return value is the same object.''',
    __new__ = newmethod(descr__new__),
    )
tuple_typedef.custom_hash = True
