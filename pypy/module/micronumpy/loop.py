
""" This file is the main run loop as well as evaluation loops for various
signatures
"""

from pypy.rlib.objectmodel import specialize
from pypy.rlib.rstring import StringBuilder
from pypy.rlib import jit
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.micronumpy.base import W_NDimArray

def call2(shape, func, name, calc_dtype, res_dtype, w_lhs, w_rhs, out):
    if out is None:
        out = W_NDimArray.from_shape(shape, res_dtype)
    left_iter = w_lhs.create_iter(shape)
    right_iter = w_rhs.create_iter(shape)
    out_iter = out.create_iter(shape)
    while not out_iter.done():
        w_left = left_iter.getitem().convert_to(calc_dtype)
        w_right = right_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, w_left, w_right).convert_to(
            res_dtype))
        left_iter.next()
        right_iter.next()
        out_iter.next()
    return out

def call1(shape, func, name, calc_dtype, res_dtype, w_obj, out):
    if out is None:
        out = W_NDimArray.from_shape(shape, res_dtype)
    obj_iter = w_obj.create_iter(shape)
    out_iter = out.create_iter(shape)
    while not out_iter.done():
        elem = obj_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, elem).convert_to(res_dtype))
        out_iter.next()
        obj_iter.next()
    return out

def setslice(shape, target, source):
    # note that unlike everything else, target and source here are
    # array implementations, not arrays
    target_iter = target.create_iter(shape)
    source_iter = source.create_iter(shape)
    dtype = target.dtype
    while not target_iter.done():
        target_iter.setitem(source_iter.getitem().convert_to(dtype))
        target_iter.next()
        source_iter.next()
    return target

def compute_reduce(obj, calc_dtype, func, done_func, identity):
    obj_iter = obj.create_iter(obj.get_shape())
    if identity is None:
        cur_value = obj_iter.getitem().convert_to(calc_dtype)
        obj_iter.next()
    else:
        cur_value = identity.convert_to(calc_dtype)
    while not obj_iter.done():
        rval = obj_iter.getitem().convert_to(calc_dtype)
        if done_func is not None and done_func(calc_dtype, rval):
            return rval
        cur_value = func(calc_dtype, cur_value, rval)
        obj_iter.next()
    return cur_value

def fill(arr, box):
    arr_iter = arr.create_iter(arr.get_shape())
    while not arr_iter.done():
        arr_iter.setitem(box)
        arr_iter.next()

def where(out, shape, arr, x, y, dtype):
    out_iter = out.create_iter(shape)
    arr_iter = arr.create_iter(shape)
    arr_dtype = arr.get_dtype()
    x_iter = x.create_iter(shape)
    y_iter = y.create_iter(shape)
    if x.is_scalar():
        if y.is_scalar():
            iter = arr_iter
        else:
            iter = y_iter
    else:
        iter = x_iter
    while not iter.done():
        w_cond = arr_iter.getitem()
        if arr_dtype.itemtype.bool(w_cond):
            w_val = x_iter.getitem().convert_to(dtype)
        else:
            w_val = y_iter.getitem().convert_to(dtype)
        out_iter.setitem(w_val)
        out_iter.next()
        arr_iter.next()
        x_iter.next()
        y_iter.next()
    return out

def do_axis_reduce(shape, func, arr, dtype, axis, out, identity):
    out_iter = out.create_axis_iter(arr.get_shape(), axis)
    arr_iter = arr.create_iter(arr.get_shape())
    if identity is not None:
        identity = identity.convert_to(dtype)
    while not out_iter.done():
        w_val = arr_iter.getitem().convert_to(dtype)
        if out_iter.first_line:
            if identity is not None:
                w_val = func(dtype, identity, w_val)
        else:
            cur = out_iter.getitem()
            w_val = func(dtype, cur, w_val)
        out_iter.setitem(w_val)
        arr_iter.next()
        out_iter.next()
    return out

@specialize.arg(0)
def argmin_argmax(op_name, arr):
    result = 0
    idx = 1
    dtype = arr.get_dtype()
    iter = arr.create_iter(arr.get_shape())
    cur_best = iter.getitem()
    iter.next()
    while not iter.done():
        w_val = iter.getitem()
        new_best = getattr(dtype.itemtype, op_name)(cur_best, w_val)
        if dtype.itemtype.ne(new_best, cur_best):
            result = idx
            cur_best = new_best
        iter.next()
        idx += 1
    return result

def multidim_dot(space, left, right, result, dtype, right_critical_dim):
    ''' assumes left, right are concrete arrays
    given left.shape == [3, 5, 7],
          right.shape == [2, 7, 4]
    then
     result.shape == [3, 5, 2, 4]
     broadcast shape should be [3, 5, 2, 7, 4]
     result should skip dims 3 which is len(result_shape) - 1
        (note that if right is 1d, result should 
                  skip len(result_shape))
     left should skip 2, 4 which is a.ndims-1 + range(right.ndims)
          except where it==(right.ndims-2)
     right should skip 0, 1
    '''
    left_shape = left.get_shape()
    right_shape = right.get_shape()
    broadcast_shape = left_shape[:-1] + right_shape
    left_skip = [len(left_shape) - 1 + i for i in range(len(right_shape))
                                         if i != right_critical_dim]
    right_skip = range(len(left_shape) - 1)
    result_skip = [len(result.get_shape()) - (len(right_shape) > 1)]
    outi = result.create_dot_iter(broadcast_shape, result_skip)
    lefti = left.create_dot_iter(broadcast_shape, left_skip)
    righti = right.create_dot_iter(broadcast_shape, right_skip)
    while not outi.done():
        lval = lefti.getitem().convert_to(dtype) 
        rval = righti.getitem().convert_to(dtype) 
        outval = outi.getitem().convert_to(dtype) 
        v = dtype.itemtype.mul(lval, rval)
        value = dtype.itemtype.add(v, outval).convert_to(dtype)
        outi.setitem(value)
        outi.next()
        righti.next()
        lefti.next()
    return result

def count_all_true(arr):
    s = 0
    if arr.is_scalar():
        return arr.get_dtype().itemtype.bool(arr.get_scalar_value())
    iter = arr.create_iter()
    while not iter.done():
        s += iter.getitem_bool()
        iter.next()
    return s

def getitem_filter(res, arr, index):
    res_iter = res.create_iter()
    index_iter = index.create_iter()
    arr_iter = arr.create_iter()
    while not index_iter.done():
        if index_iter.getitem_bool():
            res_iter.setitem(arr_iter.getitem())
            res_iter.next()
        index_iter.next()
        arr_iter.next()
    return res

def setitem_filter(arr, index, value):
    arr_iter = arr.create_iter()
    index_iter = index.create_iter()
    value_iter = value.create_iter()
    while not index_iter.done():
        if index_iter.getitem_bool():
            arr_iter.setitem(value_iter.getitem())
            value_iter.next()
        arr_iter.next()
        index_iter.next()

def flatiter_getitem(res, base_iter, step):
    ri = res.create_iter()
    while not ri.done():
        ri.setitem(base_iter.getitem())
        base_iter.next_skip_x(step)
        ri.next()
    return res

def flatiter_setitem(arr, val, start, step, length):
    dtype = arr.get_dtype()
    arr_iter = arr.create_iter()
    val_iter = val.create_iter()
    arr_iter.next_skip_x(start)
    while length > 0:
        arr_iter.setitem(val_iter.getitem().convert_to(dtype))
        # need to repeat i_nput values until all assignments are done
        arr_iter.next_skip_x(step)
        length -= 1
        val_iter.next()
        # WTF numpy?
        val_iter.reset()

def fromstring_loop(a, dtype, itemsize, s):
    i = 0
    ai = a.create_iter()
    while not ai.done():
        val = dtype.itemtype.runpack_str(s[i*itemsize:i*itemsize + itemsize])
        ai.setitem(val)
        ai.next()
        i += 1

def tostring(space, arr):
    builder = StringBuilder()
    iter = arr.create_iter()
    res_str = W_NDimArray.from_shape([1], arr.get_dtype(), order='C')
    itemsize = arr.get_dtype().itemtype.get_element_size()
    res_str_casted = rffi.cast(rffi.CArrayPtr(lltype.Char),
                               res_str.implementation.get_storage_as_int(space))
    while not iter.done():
        res_str.implementation.setitem(0, iter.getitem())
        for i in range(itemsize):
            builder.append(res_str_casted[i])
        iter.next()
    return builder.build()

class PureShapeIterator(object):
    def __init__(self, shape, idx_w):
        self.shape = shape
        self.shapelen = len(shape)
        self.indexes = [0] * len(shape)
        self._done = False
        self.idx_w = [None] * len(idx_w)
        for i, w_idx in enumerate(idx_w):
            if isinstance(w_idx, W_NDimArray):
                self.idx_w[i] = w_idx.create_iter(shape)

    def done(self):
        return self._done

    @jit.unroll_safe
    def next(self):
        for w_idx in self.idx_w:
            if w_idx is not None:
                w_idx.next()
        for i in range(self.shapelen - 1, -1, -1):
            if self.indexes[i] < self.shape[i] - 1:
                self.indexes[i] += 1
                break
            else:
                self.indexes[i] = 0
        else:
            self._done = True

    def get_index(self, space):
        return [space.wrap(i) for i in self.indexes]

def getitem_array_int(space, arr, res, iter_shape, indexes_w, prefix_w):
    iter = PureShapeIterator(iter_shape, indexes_w)
    while not iter.done():
        # prepare the index
        index_w = [None] * len(indexes_w)
        for i in range(len(indexes_w)):
            if iter.idx_w[i] is not None:
                index_w[i] = iter.idx_w[i].getitem()
            else:
                index_w[i] = indexes_w[i]
        res.descr_setitem(space, space.newtuple(prefix_w +
                                                iter.get_index(space)),
                          arr.descr_getitem(space, space.newtuple(index_w)))
        iter.next()
    return res

def setitem_array_int(space, arr, iter_shape, indexes_w, val_arr,
                      prefix_w):
    iter = PureShapeIterator(iter_shape, indexes_w)
    while not iter.done():
        # prepare the index
        index_w = [None] * len(indexes_w)
        for i in range(len(indexes_w)):
            if iter.idx_w[i] is not None:
                index_w[i] = iter.idx_w[i].getitem()
            else:
                index_w[i] = indexes_w[i]
        w_idx = space.newtuple(prefix_w + iter.get_index(space))
        arr.descr_setitem(space, space.newtuple(index_w),
                          val_arr.descr_getitem(space, w_idx))
        iter.next()

