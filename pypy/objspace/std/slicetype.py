from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from typeobject import W_TypeObject


class W_SliceType(W_TypeObject):

    typename = 'slice'

    slice_indices = MultiMethod('indices', 2)


registerimplementation(W_SliceType)


def type_new__SliceType_SliceType(space, w_basetype, w_slicetype, w_args, w_kwds):
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
    return space.unwrap(w_1), space.unwrap(w_2), space.unwrap(w_3)

def indices4(space, w_slice, length):
    w_result = slice_indices4(space, w_slice, space.wrap(length))
    w_1, w_2, w_3, w_4 = space.unpacktuple(w_result, 4)
    return (space.unwrap(w_1), space.unwrap(w_2),
            space.unwrap(w_3), space.unwrap(w_4))


register_all(vars(), W_SliceType)
