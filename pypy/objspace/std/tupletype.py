from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_TupleType(W_TypeObject):

    typename = 'tuple'

registerimplementation(W_TupleType)


def type_new__TupleType_TupleType_ANY_ANY(space, w_basetype, w_tupletype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        tuple_w = []
    elif len(args) == 1:
        tuple_w = space.unpackiterable(args[0])
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("tuple() takes at most 1 argument"))
    return space.newtuple(tuple_w), True

register_all(vars())
