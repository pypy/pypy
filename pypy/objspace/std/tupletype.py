from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_TupleType(W_TypeObject):

    typename = 'tuple'

registerimplementation(W_TupleType)


# XXX we'll worry about the __new__/__init__ distinction later
def tupletype_new(space, w_tupletype, w_args, w_kwds):
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
    return space.newtuple(tuple_w)

StdObjSpace.new.register(tupletype_new, W_TupleType, W_ANY, W_ANY)
