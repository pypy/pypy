from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_SliceType(W_TypeObject):

    typename = 'slice'

registerimplementation(W_SliceType)


def type_new__SliceType_SliceType_ANY_ANY(space, w_basetype, w_slicetype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    start = space.w_None
    stop = space.w_None
    step = space.w_None
    if len(args) == 1:
        stop, = args
    elif len(args) == 2:
        start, stop = args
    elif len(args) == 3:
        start, stop, step = args        
    elif len(args) > 3:
        raise OperationError(space.w_TypeError,
                             space.wrap("slice() takes at most 3 arguments"))
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("slice() takes at least 1 argument"))
    return space.newslice(start, stop, step), True

register_all(vars())
