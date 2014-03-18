from pypy.interpreter.error import OperationError, oefmt
from rpython.rlib import jit
from pypy.module.micronumpy import support, constants as NPY
from pypy.module.micronumpy.base import W_NDimArray


# structures to describe slicing

class BaseChunk(object):
    pass


class RecordChunk(BaseChunk):
    def __init__(self, name):
        self.name = name

    def apply(self, space, orig_arr):
        arr = orig_arr.implementation
        ofs, subdtype = arr.dtype.fields[self.name]
        # ofs only changes start
        # create a view of the original array by extending
        # the shape, strides, backstrides of the array
        strides, backstrides = calc_strides(subdtype.shape,
                                            subdtype.subdtype, arr.order)
        final_shape = arr.shape + subdtype.shape
        final_strides = arr.get_strides() + strides
        final_backstrides = arr.get_backstrides() + backstrides
        final_dtype = subdtype
        if subdtype.subdtype:
            final_dtype = subdtype.subdtype
        return W_NDimArray.new_slice(space, arr.start + ofs, final_strides,
                                     final_backstrides,
                                     final_shape, arr, orig_arr, final_dtype)


class Chunks(BaseChunk):
    def __init__(self, l):
        self.l = l

    @jit.unroll_safe
    def extend_shape(self, old_shape):
        shape = []
        i = -1
        for i, c in enumerate_chunks(self.l):
            if c.step != 0:
                shape.append(c.lgt)
        s = i + 1
        assert s >= 0
        return shape[:] + old_shape[s:]

    def apply(self, space, orig_arr):
        arr = orig_arr.implementation
        shape = self.extend_shape(arr.shape)
        r = calculate_slice_strides(arr.shape, arr.start, arr.get_strides(),
                                    arr.get_backstrides(), self.l)
        _, start, strides, backstrides = r
        return W_NDimArray.new_slice(space, start, strides[:], backstrides[:],
                                     shape[:], arr, orig_arr)


class Chunk(BaseChunk):
    axis_step = 1

    def __init__(self, start, stop, step, lgt):
        self.start = start
        self.stop = stop
        self.step = step
        self.lgt = lgt

    def __repr__(self):
        return 'Chunk(%d, %d, %d, %d)' % (self.start, self.stop, self.step,
                                          self.lgt)


class NewAxisChunk(Chunk):
    start = 0
    stop = 1
    step = 1
    lgt = 1
    axis_step = 0

    def __init__(self):
        pass


class BaseTransform(object):
    pass


class ViewTransform(BaseTransform):
    def __init__(self, chunks):
        # 4-tuple specifying slicing
        self.chunks = chunks


class BroadcastTransform(BaseTransform):
    def __init__(self, res_shape):
        self.res_shape = res_shape


@jit.look_inside_iff(lambda chunks: jit.isconstant(len(chunks)))
def enumerate_chunks(chunks):
    result = []
    i = -1
    for chunk in chunks:
        i += chunk.axis_step
        result.append((i, chunk))
    return result


@jit.look_inside_iff(lambda shape, start, strides, backstrides, chunks:
                     jit.isconstant(len(chunks)))
def calculate_slice_strides(shape, start, strides, backstrides, chunks):
    size = 0
    for chunk in chunks:
        if chunk.step != 0:
            size += 1
    rstrides = [0] * size
    rbackstrides = [0] * size
    rstart = start
    rshape = [0] * size
    i = -1
    j = 0
    for i, chunk in enumerate_chunks(chunks):
        try:
            s_i = strides[i]
        except IndexError:
            continue
        if chunk.step != 0:
            rstrides[j] = s_i * chunk.step
            rbackstrides[j] = s_i * max(0, chunk.lgt - 1) * chunk.step
            rshape[j] = chunk.lgt
            j += 1
        rstart += s_i * chunk.start
    # add a reminder
    s = i + 1
    assert s >= 0
    rstrides += strides[s:]
    rbackstrides += backstrides[s:]
    rshape += shape[s:]
    return rshape, rstart, rstrides, rbackstrides


def calculate_broadcast_strides(strides, backstrides, orig_shape, res_shape, backwards=False):
    rstrides = []
    rbackstrides = []
    for i in range(len(orig_shape)):
        if orig_shape[i] == 1:
            rstrides.append(0)
            rbackstrides.append(0)
        else:
            rstrides.append(strides[i])
            rbackstrides.append(backstrides[i])
    if backwards:
        rstrides = rstrides + [0] * (len(res_shape) - len(orig_shape))
        rbackstrides = rbackstrides + [0] * (len(res_shape) - len(orig_shape))
    else:
        rstrides = [0] * (len(res_shape) - len(orig_shape)) + rstrides
        rbackstrides = [0] * (len(res_shape) - len(orig_shape)) + rbackstrides
    return rstrides, rbackstrides


def is_single_elem(space, w_elem, is_rec_type):
    if (is_rec_type and space.isinstance_w(w_elem, space.w_tuple)):
        return True
    if (space.isinstance_w(w_elem, space.w_tuple) or
            space.isinstance_w(w_elem, space.w_list)):
        return False
    if isinstance(w_elem, W_NDimArray) and not w_elem.is_scalar():
        return False
    return True


def find_shape_and_elems(space, w_iterable, dtype):
    isstr = space.isinstance_w(w_iterable, space.w_str)
    if not support.issequence_w(space, w_iterable) or isstr:
        if dtype is None or dtype.char != NPY.CHARLTR:
            return [], [w_iterable]
    is_rec_type = dtype is not None and dtype.is_record()
    if is_rec_type and is_single_elem(space, w_iterable, is_rec_type):
        return [], [w_iterable]
    if isinstance(w_iterable, W_NDimArray) and w_iterable.is_scalar():
        return [], [w_iterable]
    return _find_shape_and_elems(space, w_iterable, is_rec_type)


def _find_shape_and_elems(space, w_iterable, is_rec_type):
    shape = [space.len_w(w_iterable)]
    batch = space.listview(w_iterable)
    while True:
        if not batch:
            return shape[:], []
        if is_single_elem(space, batch[0], is_rec_type):
            for w_elem in batch:
                if not is_single_elem(space, w_elem, is_rec_type):
                    raise OperationError(space.w_ValueError, space.wrap(
                        "setting an array element with a sequence"))
            return shape[:], batch
        new_batch = []
        size = space.len_w(batch[0])
        for w_elem in batch:
            if (is_single_elem(space, w_elem, is_rec_type) or
                    space.len_w(w_elem) != size):
                raise OperationError(space.w_ValueError, space.wrap(
                    "setting an array element with a sequence"))
            w_array = space.lookup(w_elem, '__array__')
            if w_array is not None:
                # Make sure we call the array implementation of listview,
                # since for some ndarray subclasses (matrix, for instance)
                # listview does not reduce but rather returns the same class
                w_elem = space.get_and_call_function(w_array, w_elem, space.w_None)
            new_batch += space.listview(w_elem)
        shape.append(size)
        batch = new_batch


def find_dtype_for_seq(space, elems_w, dtype):
    from pypy.module.micronumpy.ufuncs import find_dtype_for_scalar
    if len(elems_w) == 1:
        w_elem = elems_w[0]
        if isinstance(w_elem, W_NDimArray) and w_elem.is_scalar():
            w_elem = w_elem.get_scalar_value()
        return find_dtype_for_scalar(space, w_elem, dtype)
    return _find_dtype_for_seq(space, elems_w, dtype)


def _find_dtype_for_seq(space, elems_w, dtype):
    from pypy.module.micronumpy.ufuncs import find_dtype_for_scalar
    for w_elem in elems_w:
        if isinstance(w_elem, W_NDimArray) and w_elem.is_scalar():
            w_elem = w_elem.get_scalar_value()
        dtype = find_dtype_for_scalar(space, w_elem, dtype)
    return dtype


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


@jit.unroll_safe
def shape_agreement(space, shape1, w_arr2, broadcast_down=True):
    if w_arr2 is None:
        return shape1
    assert isinstance(w_arr2, W_NDimArray)
    shape2 = w_arr2.get_shape()
    ret = _shape_agreement(shape1, shape2)
    if len(ret) < max(len(shape1), len(shape2)):
        raise OperationError(space.w_ValueError,
            space.wrap("operands could not be broadcast together with shapes (%s) (%s)" % (
                ",".join([str(x) for x in shape1]),
                ",".join([str(x) for x in shape2]),
            ))
        )
    if not broadcast_down and len([x for x in ret if x != 1]) > len([x for x in shape2 if x != 1]):
        raise OperationError(space.w_ValueError,
            space.wrap("unbroadcastable shape (%s) cannot be broadcasted to (%s)" % (
                ",".join([str(x) for x in shape1]),
                ",".join([str(x) for x in shape2]),
            ))
        )
    return ret


@jit.unroll_safe
def shape_agreement_multiple(space, array_list):
    """ call shape_agreement recursively, allow elements from array_list to
    be None (like w_out)
    """
    shape = array_list[0].get_shape()
    for arr in array_list[1:]:
        if not space.is_none(arr):
            shape = shape_agreement(space, shape, arr)
    return shape


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
        new_shape = []
        i = 0
        for elem in batch:
            s = space.int_w(elem)
            if s < 0:
                if neg_dim >= 0:
                    raise oefmt(space.w_ValueError,
                        "can only specify one unknown dimension")
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


@jit.unroll_safe
def calc_strides(shape, dtype, order):
    strides = []
    backstrides = []
    s = 1
    shape_rev = shape[:]
    if order == 'C':
        shape_rev.reverse()
    for sh in shape_rev:
        slimit = max(sh, 1)
        strides.append(s * dtype.elsize)
        backstrides.append(s * (slimit - 1) * dtype.elsize)
        s *= slimit
    if order == 'C':
        strides.reverse()
        backstrides.reverse()
    return strides, backstrides


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
    return new_strides[:]
