from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_FloatType(W_TypeObject):

    typename = 'float'

def new__FloatType_ANY_ANY(space, w_inttype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        return space.newint(0)
    elif len(args) == 1:
        arg = args[0]
        if space.is_true(space.issubtype(space.type(arg),
                                         space.w_str)):
            try:
                return space.newfloat(float(space.unwrap(arg)))
            except TypeError:
                raise OperationError(space.w_TypeError,
                                     space.wrap("invalid literal for float()"))
        else:
            return space.float(args[0])
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("float() takes at most 1 argument"))

register_all(vars())
