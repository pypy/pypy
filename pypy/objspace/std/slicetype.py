import sys
from pypy.interpreter import baseobjspace
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.interpreter.error import OperationError

# indices multimehtod
slice_indices = SMM('indices', 2,
                    doc='S.indices(len) -> (start, stop, stride)\n\nAssuming a'
                        ' sequence of length len, calculate the start and'
                        ' stop\nindices, and the stride length of the extended'
                        ' slice described by\nS. Out of bounds indices are'
                        ' clipped in a manner consistent with the\nhandling of'
                        ' normal slices.')

# utility functions
def _Eval_SliceIndex(space, w_int):
    return space.getindex_w(w_int) # clamp if long integer is too large
    # This is done by getindex_w already.
    #try:
    #    x = space.getindex_w(w_int)
    #except OperationError, e:
    #    if not e.match(space, space.w_OverflowError):
    #        raise
    #    cmp = space.is_true(space.ge(w_int, space.wrap(0)))
    #    if cmp:
    #        x = sys.maxint
    #    else:
    #        x = -sys.maxint
    #return x

def adapt_bound(space, w_index, w_size):
    if not (space.is_true(space.isinstance(w_index, space.w_int)) or
            space.is_true(space.isinstance(w_index, space.w_long))):
        raise OperationError(space.w_TypeError,
                             space.wrap("slice indices must be integers"))
    if space.is_true(space.lt(w_index, space.wrap(0))):
        w_index = space.add(w_index, w_size)
        if space.is_true(space.lt(w_index, space.wrap(0))):
            w_index = space.wrap(0)
    if space.is_true(space.gt(w_index, w_size)):
        w_index = w_size
    return w_index

register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_slicetype, args_w):
    from pypy.objspace.std.sliceobject import W_SliceObject
    w_start = space.w_None
    w_stop = space.w_None
    w_step = space.w_None
    if len(args_w) == 1:
        w_stop, = args_w
    elif len(args_w) == 2:
        w_start, w_stop = args_w
    elif len(args_w) == 3:
        w_start, w_stop, w_step = args_w
    elif len(args_w) > 3:
        raise OperationError(space.w_TypeError,
                             space.wrap("slice() takes at most 3 arguments"))
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("slice() takes at least 1 argument"))
    w_obj = space.allocate_instance(W_SliceObject, w_slicetype)
    W_SliceObject.__init__(w_obj, w_start, w_stop, w_step)
    return w_obj
#
descr__new__.unwrap_spec = [baseobjspace.ObjSpace, baseobjspace.W_Root,
                            'args_w']

# ____________________________________________________________

def slicewprop(name):
    def fget(space, w_obj):
        from pypy.objspace.std.sliceobject import W_SliceObject
        if not isinstance(w_obj, W_SliceObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("descriptor is for 'slice'"))
        return getattr(w_obj, name)
    return GetSetProperty(fget)


slice_typedef = StdTypeDef("slice",
    __doc__ = '''slice([start,] stop[, step])

Create a slice object.  This is used for extended slicing (e.g. a[0:10:2]).''',
    __new__ = newmethod(descr__new__),
    __hash__ = no_hash_descr,
    start = slicewprop('w_start'),
    stop  = slicewprop('w_stop'),
    step  = slicewprop('w_step'),
    )
slice_typedef.registermethods(globals())
