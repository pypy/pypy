"""
Reviewed 03-06-21
"""

from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject
from inttype import W_IntType


class W_BoolType(W_TypeObject):

    typename = 'bool'
    staticbases = (W_IntType,)

registerimplementation(W_BoolType)

def type_new__BoolType_BoolType(space, w_basetype, w_booltype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        return space.w_False, True
    elif len(args) == 1:
        arg = args[0]
        if space.is_true(arg):
            return space.w_True, True
        else:
            return space.w_False, True
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("bool() takes at most 1 argument"))

register_all(vars())
