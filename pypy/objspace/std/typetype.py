from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_TypeType(W_TypeObject):

    typename = 'type'


# hack that in place
W_TypeObject.statictype = W_TypeType


# XXX we'll worry about the __new__/__init__ distinction later
def typetype_new(space, w_typetype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 1:
        return space.type(args[0])
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("XXX sorry, type() with anything else "
                                        "but 1 argument is for later"))

StdObjSpace.new.register(typetype_new, W_TypeType, W_ANY, W_ANY)
