from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_IntType(W_TypeObject):

    typename = 'int'


# XXX we'll worry about the __new__/__init__ distinction later
def inttype_new(space, w_inttype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        return space.newint(0)
    elif len(args) == 1:
        return space.newint(space.unwrap(args[0]))
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("int() takes at most 1 argument"))

StdObjSpace.new.register(inttype_new, W_IntType, W_ANY, W_ANY)
