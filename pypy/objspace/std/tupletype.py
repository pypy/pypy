import sys
from pypy.interpreter import gateway
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM

def wraptuple(space, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject
    if space.config.objspace.std.withsmalltuple:
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject2
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject3
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject4
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject5
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject6
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject7
        from pypy.objspace.std.smalltupleobject import W_SmallTupleObject8
        if len(list_w) == 2:
            return W_SmallTupleObject2(list_w)
        if len(list_w) == 3:
            return W_SmallTupleObject3(list_w)
        if len(list_w) == 4:
            return W_SmallTupleObject4(list_w)
        if len(list_w) == 5:
            return W_SmallTupleObject5(list_w)
        if len(list_w) == 6:
            return W_SmallTupleObject6(list_w)
        if len(list_w) == 7:
            return W_SmallTupleObject7(list_w)
        if len(list_w) == 8:
            return W_SmallTupleObject8(list_w)
    return W_TupleObject(list_w)

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
