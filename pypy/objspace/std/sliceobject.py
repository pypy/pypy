"""
Reviewed 03-06-21

slice object construction   tested, OK
indices method              tested, OK
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway


class W_SliceObject(W_Object):
    from pypy.objspace.std.slicetype import slice_typedef as typedef
    
    def __init__(w_self, space, w_start, w_stop, w_step):
        W_Object.__init__(w_self, space)
        w_self.w_start = w_start
        w_self.w_stop = w_stop
        w_self.w_step = w_step

registerimplementation(W_SliceObject)

def app_repr__Slice(aslice):
    return 'slice(%r, %r, %r)' % (aslice.start, aslice.stop, aslice.step)

repr__Slice = gateway.app2interp(app_repr__Slice)

def eq__Slice_Slice(space, w_slice1, w_slice2):
    # We need this because CPython considers that slice1 == slice1
    # is *always* True (e.g. even if slice1 was built with non-comparable
    # parameters
    if space.is_w(w_slice1, w_slice2):
        return space.w_True
    if space.eq_w(w_slice1.w_start, w_slice2.w_start) and \
        space.eq_w(w_slice1.w_stop, w_slice2.w_stop) and \
        space.eq_w(w_slice1.w_step, w_slice2.w_step):
        return space.w_True
    else:
        return space.w_False

def hash__Slice(space, w_slice):
    """space are not hashables but they must have a __hash__ method"""
    raise OperationError(space.w_TypeError,
                         space.wrap("unhashable type"))

register_all(vars())
