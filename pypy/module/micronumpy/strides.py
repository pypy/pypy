from pypy.rlib import jit
from pypy.interpreter.error import OperationError


@jit.look_inside_iff(lambda shape, start, strides, backstrides, chunks:
    jit.isconstant(len(chunks))
)
def calculate_slice_strides(shape, start, strides, backstrides, chunks):
    rstrides = []
    rbackstrides = []
    rstart = start
    rshape = []
    i = -1
    for i, chunk in enumerate(chunks):
        if chunk.step != 0:
            rstrides.append(strides[i] * chunk.step)
            rbackstrides.append(strides[i] * (chunk.lgt - 1) * chunk.step)
            rshape.append(chunk.lgt)
        rstart += strides[i] * chunk.start
    # add a reminder
    s = i + 1
    assert s >= 0
    rstrides += strides[s:]
    rbackstrides += backstrides[s:]
    rshape += shape[s:]
    return rshape, rstart, rstrides, rbackstrides

def calculate_broadcast_strides(strides, backstrides, orig_shape, res_shape):
    rstrides = []
    rbackstrides = []
    for i in range(len(orig_shape)):
        if orig_shape[i] == 1:
            rstrides.append(0)
            rbackstrides.append(0)
        else:
            rstrides.append(strides[i])
            rbackstrides.append(backstrides[i])
    rstrides = [0] * (len(res_shape) - len(orig_shape)) + rstrides
    rbackstrides = [0] * (len(res_shape) - len(orig_shape)) + rbackstrides
    return rstrides, rbackstrides

def to_coords(space, shape, size, order, w_item_or_slice):
    '''Returns a start coord, step, and length.
    '''
    start = lngth = step = 0
    if not (space.isinstance_w(w_item_or_slice, space.w_int) or
        space.isinstance_w(w_item_or_slice, space.w_slice)):
        raise OperationError(space.w_IndexError,
                             space.wrap('unsupported iterator index'))
            
    start, stop, step, lngth = space.decode_index4(w_item_or_slice, size)
        
    coords = [0] * len(shape)
    i = start
    if order == 'C':
        for s in range(len(shape) -1, -1, -1):
            coords[s] = i % shape[s]
            i //= shape[s]
    else:
        for s in range(len(shape)):
            coords[s] = i % shape[s]
            i //= shape[s]

    return coords, step, lngth
