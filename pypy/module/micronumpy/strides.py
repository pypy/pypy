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

def find_shape_and_elems(space, w_iterable):
    shape = [space.len_w(w_iterable)]
    batch = space.listview(w_iterable)
    while True:
        new_batch = []
        if not batch:
            return shape, []
        if not space.issequence_w(batch[0]):
            for elem in batch:
                if space.issequence_w(elem):
                    raise OperationError(space.w_ValueError, space.wrap(
                        "setting an array element with a sequence"))
            return shape, batch
        size = space.len_w(batch[0])
        for w_elem in batch:
            if not space.issequence_w(w_elem) or space.len_w(w_elem) != size:
                raise OperationError(space.w_ValueError, space.wrap(
                    "setting an array element with a sequence"))
            new_batch += space.listview(w_elem)
        shape.append(size)
        batch = new_batch

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

def shape_agreement(space, shape1, shape2):
    ret = _shape_agreement(shape1, shape2)
    if len(ret) < max(len(shape1), len(shape2)):
        raise OperationError(space.w_ValueError,
            space.wrap("operands could not be broadcast together with shapes (%s) (%s)" % (
                ",".join([str(x) for x in shape1]),
                ",".join([str(x) for x in shape2]),
            ))
        )
    return ret

def _shape_agreement(shape1, shape2):
    """ Checks agreement about two shapes with respect to broadcasting. Returns
    the resulting shape.
    """
    lshift = 0
    rshift = 0
    if len(shape1) > len(shape2):
        m = len(shape1)
        n = len(shape2)
        rshift = len(shape2) - len(shape1)
        remainder = shape1
    else:
        m = len(shape2)
        n = len(shape1)
        lshift = len(shape1) - len(shape2)
        remainder = shape2
    endshape = [0] * m
    indices1 = [True] * m
    indices2 = [True] * m
    for i in range(m - 1, m - n - 1, -1):
        left = shape1[i + lshift]
        right = shape2[i + rshift]
        if left == right:
            endshape[i] = left
        elif left == 1:
            endshape[i] = right
            indices1[i + lshift] = False
        elif right == 1:
            endshape[i] = left
            indices2[i + rshift] = False
        else:
            return []
            #raise OperationError(space.w_ValueError, space.wrap(
            #    "frames are not aligned"))
    for i in range(m - n):
        endshape[i] = remainder[i]
    return endshape

def get_shape_from_iterable(space, old_size, w_iterable):
    new_size = 0
    new_shape = []
    if space.isinstance_w(w_iterable, space.w_int):
        new_size = space.int_w(w_iterable)
        if new_size < 0:
            new_size = old_size
        new_shape = [new_size]
    else:
        neg_dim = -1
        batch = space.listview(w_iterable)
        new_size = 1
        if len(batch) < 1:
            if old_size == 1:
                # Scalars can have an empty size.
                new_size = 1
            else:
                new_size = 0
        new_shape = []
        i = 0
        for elem in batch:
            s = space.int_w(elem)
            if s < 0:
                if neg_dim >= 0:
                    raise OperationError(space.w_ValueError, space.wrap(
                             "can only specify one unknown dimension"))
                s = 1
                neg_dim = i
            new_size *= s
            new_shape.append(s)
            i += 1
        if neg_dim >= 0:
            new_shape[neg_dim] = old_size / new_size
            new_size *= new_shape[neg_dim]
    if new_size != old_size:
        raise OperationError(space.w_ValueError,
                space.wrap("total size of new array must be unchanged"))
    return new_shape

# Recalculating strides. Find the steps that the iteration does for each
# dimension, given the stride and shape. Then try to create a new stride that
# fits the new shape, using those steps. If there is a shape/step mismatch
# (meaning that the realignment of elements crosses from one step into another)
# return None so that the caller can raise an exception.
def calc_new_strides(new_shape, old_shape, old_strides, order):
    # Return the proper strides for new_shape, or None if the mapping crosses
    # stepping boundaries

    # Assumes that prod(old_shape) == prod(new_shape), len(old_shape) > 1, and
    # len(new_shape) > 0
    steps = []
    last_step = 1
    oldI = 0
    new_strides = []
    if order == 'F':
        for i in range(len(old_shape)):
            steps.append(old_strides[i] / last_step)
            last_step *= old_shape[i]
        cur_step = steps[0]
        n_new_elems_used = 1
        n_old_elems_to_use = old_shape[0]
        for s in new_shape:
            new_strides.append(cur_step * n_new_elems_used)
            n_new_elems_used *= s
            while n_new_elems_used > n_old_elems_to_use:
                oldI += 1
                if steps[oldI] != steps[oldI - 1]:
                    return None
                n_old_elems_to_use *= old_shape[oldI]
            if n_new_elems_used == n_old_elems_to_use:
                oldI += 1
                if oldI < len(old_shape):
                    cur_step = steps[oldI]
                    n_old_elems_to_use *= old_shape[oldI]
    elif order == 'C':
        for i in range(len(old_shape) - 1, -1, -1):
            steps.insert(0, old_strides[i] / last_step)
            last_step *= old_shape[i]
        cur_step = steps[-1]
        n_new_elems_used = 1
        oldI = -1
        n_old_elems_to_use = old_shape[-1]
        for i in range(len(new_shape) - 1, -1, -1):
            s = new_shape[i]
            new_strides.insert(0, cur_step * n_new_elems_used)
            n_new_elems_used *= s
            while n_new_elems_used > n_old_elems_to_use:
                oldI -= 1
                if steps[oldI] != steps[oldI + 1]:
                    return None
                n_old_elems_to_use *= old_shape[oldI]
            if n_new_elems_used == n_old_elems_to_use:
                oldI -= 1
                if oldI >= -len(old_shape):
                    cur_step = steps[oldI]
                    n_old_elems_to_use *= old_shape[oldI]
    assert len(new_strides) == len(new_shape)
    return new_strides
