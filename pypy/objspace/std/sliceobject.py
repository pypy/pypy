"""
Reviewed 03-06-21

slice object construction   tested, OK
indices method              tested, OK
"""

from pypy.objspace.std.objspace import *
from slicetype import W_SliceType


class W_SliceObject(W_Object):
    statictype = W_SliceType
    
    def __init__(w_self, space, w_start, w_stop, w_step):
        W_Object.__init__(w_self, space)
        w_self.w_start = w_start
        w_self.w_stop = w_stop
        w_self.w_step = w_step

registerimplementation(W_SliceObject)


def getattr__Slice_ANY(space, w_slice, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('start'))):
        if w_slice.w_start is None:
            return space.w_None
        else:
            return w_slice.w_start
    if space.is_true(space.eq(w_attr, space.wrap('stop'))):
        if w_slice.w_stop is None:
            return space.w_None
        else:
            return w_slice.w_stop
    if space.is_true(space.eq(w_attr, space.wrap('step'))):
        if w_slice.w_step is None:
            return space.w_None
        else:
            return w_slice.w_step
    raise FailedToImplement(space.w_AttributeError)

register_all(vars())
