from pypy.interpreter import baseobjspace, gateway
from pypy.interpreter.typedef import GetSetProperty
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
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
def eval_slice_index(space, w_int):
    try:
        return space.getindex_w(w_int, None) # clamp if long integer too large
    except OperationError, err:
        if not err.match(space, space.w_TypeError):
            raise
        raise OperationError(space.w_TypeError,
                             space.wrap("slice indices must be integers or "
                                        "None or have an __index__ method"))

def adapt_lower_bound(space, size, w_index):
    index = eval_slice_index(space, w_index)
    if index < 0:
        index = index + size
        if index < 0:
            index = 0
    assert index >= 0
    return index

def adapt_bound(space, size, w_index):
    index = eval_slice_index(space, w_index)
    if index < 0:
        index = index + size
        if index < 0:
            index = 0
    if index > size:
        index = size
    assert index >= 0
    return index

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

def descr__reduce__(space, w_self):
    from pypy.objspace.std.sliceobject import W_SliceObject
    assert isinstance(w_self, W_SliceObject)
    return space.newtuple([
        space.type(w_self),
        space.newtuple([w_self.w_start,
                        w_self.w_stop,
                        w_self.w_step]),
        ])

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
    __new__ = gateway.interp2app(descr__new__),
    __hash__ = None,
    __reduce__ = gateway.interp2app(descr__reduce__),
    start = slicewprop('w_start'),
    stop  = slicewprop('w_stop'),
    step  = slicewprop('w_step'),
    )
slice_typedef.acceptable_as_base_class = False
slice_typedef.registermethods(globals())
