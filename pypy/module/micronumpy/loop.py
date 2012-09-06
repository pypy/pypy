
""" This file is the main run loop as well as evaluation loops for various
signatures
"""

from pypy.rlib.objectmodel import specialize
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

def where(out, arr, x, y, dtype):
    out_iter = out.create_iter()
    arr_iter = arr.create_iter()
    x_iter = x.create_iter()
    y_iter = y.create_iter()
    while not arr_iter.done():
        w_cond = arr_iter.getitem()
        if dtype.itemtype.bool(w_cond):
            w_val = x_iter.getitem().convert_to(dtype)
        else:
            w_val = y_iter.getitem().convert_to(dtype)
        out_iter.setitem(w_val)
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
    value_iter = value.create_iter(arr.get_shape())
    while not arr_iter.done():
        if index_iter.getitem_bool():
            arr_iter.setitem(value_iter.getitem())
        arr_iter.next()
        index_iter.next()
        value_iter.next()
