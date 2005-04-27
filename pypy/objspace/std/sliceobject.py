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
        assert w_start is not None
        assert w_stop is not None
        assert w_step is not None
        w_self.w_start = w_start
        w_self.w_stop = w_stop
        w_self.w_step = w_step

    def unwrap(w_slice):
        space = w_slice.space
        return slice(space.unwrap(w_slice.w_start), space.unwrap(w_slice.w_stop), space.unwrap(w_slice.w_step))

registerimplementation(W_SliceObject)

repr__Slice = gateway.applevel("""
    def repr__Slice(aslice):
        return 'slice(%r, %r, %r)' % (aslice.start, aslice.stop, aslice.step)
""", filename=__file__).interphook("repr__Slice")

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

def lt__Slice_Slice(space, w_slice1, w_slice2):
    if space.is_w(w_slice1, w_slice2):
        return space.w_False   # see comments in eq__Slice_Slice()
    if space.eq_w(w_slice1.w_start, w_slice2.w_start):
        if space.eq_w(w_slice1.w_stop, w_slice2.w_stop):
            return space.lt(w_slice1.w_step, w_slice2.w_step)
        else:
            return space.lt(w_slice1.w_stop, w_slice2.w_stop)
    else:
        return space.lt(w_slice1.w_start, w_slice2.w_start)

def hash__Slice(space, w_slice):
    """slices are not hashables but they must have a __hash__ method"""
    raise OperationError(space.w_TypeError,
                         space.wrap("unhashable type"))

register_all(vars())
