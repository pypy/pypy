from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_IntType(W_TypeObject):

    typename = 'int'

registerimplementation(W_IntType)


def type_new__IntType_IntType_ANY_ANY(space, w_basetype, w_inttype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        return space.newint(0), True
    elif len(args) == 1:
        arg = args[0]
        if space.is_true(space.issubtype(space.type(arg),
                                         space.w_str)):
            try:
                return space.newint(int(space.unwrap(arg))), True
            except TypeError:
                raise OperationError(space.w_TypeError,
                                     space.wrap("invalid literal for int()"))
        else:
            return space.int(args[0]), True
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("int() takes at most 1 argument"))

register_all(vars())
