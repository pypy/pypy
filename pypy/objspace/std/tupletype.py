import sys
from pypy.interpreter import gateway
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM


tuple_count = SMM("count", 2,
                  doc="count(obj) -> number of times obj appears in the tuple")

tuple_index = SMM("index", 4, defaults=(0, sys.maxint),
                  doc="index(obj, [start, [stop]]) -> first index that obj "
                  "appears in the tuple")


def descr__new__(space, w_tupletype, w_sequence=gateway.NoneNotWrapped):
    from pypy.objspace.std.tupleobject import W_TupleObject
    if w_sequence is None:
        tuple_w = []
    elif (space.is_w(w_tupletype, space.w_tuple) and
          space.is_w(space.type(w_sequence), space.w_tuple)):
        return w_sequence
    else:
        tuple_w = space.fixedview(w_sequence)
    w_obj = space.allocate_instance(W_TupleObject, w_tupletype)
    W_TupleObject.__init__(w_obj, tuple_w)
    return w_obj

# ____________________________________________________________

tuple_typedef = StdTypeDef("tuple",
    __doc__ = '''tuple() -> an empty tuple
tuple(sequence) -> tuple initialized from sequence's items

If the argument is a tuple, the return value is the same object.''',
    __new__ = gateway.interp2app(descr__new__),
    )
tuple_typedef.registermethods(globals())
