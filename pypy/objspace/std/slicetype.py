from pypy.interpreter import baseobjspace
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.interpreter.error import OperationError

slice_indices = MultiMethod('indices', 2)

# default application-level implementations for some operations

def app_slice_indices3(slice, length):
    # this is used internally, analogous to CPython's PySlice_GetIndicesEx
    step = slice.step
    if step is None:
        step = 1
    elif step == 0:
        raise ValueError, "slice step cannot be zero"
    if step < 0:
        defstart = length - 1
        defstop = -1
    else:
        defstart = 0
        defstop = length

    start = slice.start
    if start is None:
        start = defstart
    else:
        if start < 0:
            start += length
            if start < 0:
                if step < 0:
                    start = -1
                else:
                    start = 0
        elif start >= length:
            if step < 0:
                start = length - 1
            else:
                start = length

    stop = slice.stop
    if stop is None:
        stop = defstop
    else:
        if stop < 0:
            stop += length
            if stop < 0:
                stop = -1
        elif stop > length:
            stop = length

    return start, stop, step
slice_indices__ANY_ANY = slice_indices3 = gateway.app2interp(app_slice_indices3)

def app_slice_indices4(slice, sequencelength):
    start, stop, step = slice_indices3(slice, sequencelength)
    slicelength = stop - start
    lengthsign = cmp(slicelength, 0)
    stepsign = cmp(step, 0)
    if stepsign == lengthsign:
        slicelength = (slicelength - lengthsign) // step + 1
    else:
        slicelength = 0

    return start, stop, step, slicelength
slice_indices4 = gateway.app2interp(app_slice_indices4)

# utility functions
def indices3(space, w_slice, length):
    w_result = slice_indices3(space, w_slice, space.wrap(length))
    w_1, w_2, w_3 = space.unpacktuple(w_result, 3)
    return space.int_w(w_1), space.int_w(w_2), space.int_w(w_3)

def indices4(space, w_slice, length):
    w_result = slice_indices4(space, w_slice, space.wrap(length))
    w_1, w_2, w_3, w_4 = space.unpacktuple(w_result, 4)
    return (space.int_w(w_1), space.int_w(w_2),
            space.int_w(w_3), space.int_w(w_4))

def adapt_bound(space, w_index, w_size):
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
    w_obj.__init__(space, w_start, w_stop, w_step)
    return w_obj
#
descr__new__.unwrap_spec = [baseobjspace.ObjSpace, baseobjspace.W_Root,
                            'args_w']

# ____________________________________________________________

slice_typedef = StdTypeDef("slice",
    __new__ = newmethod(descr__new__),
    start = attrproperty_w('w_start'),
    stop  = attrproperty_w('w_stop'),
    step  = attrproperty_w('w_step'),
    )
slice_typedef.registermethods(globals())
