from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_FloatType(W_TypeObject):

    typename = 'float'

registerimplementation(W_FloatType)


def type_new__FloatType_FloatType_ANY_ANY(space, w_basetype, w_floattype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        return space.newfloat(0), True
    elif len(args) == 1:
        arg = args[0]
        if space.is_true(space.issubtype(space.type(arg),
                                         space.w_str)):
            try:
                return space.newfloat(float(space.unwrap(arg))), True
            except TypeError:
                raise OperationError(space.w_TypeError,
                                     space.wrap("invalid literal for float()"))
        else:
            return space.float(args[0]), True
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("float() takes at most 1 argument"))

register_all(vars())
