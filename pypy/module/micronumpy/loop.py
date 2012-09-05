
""" This file is the main run loop as well as evaluation loops for various
signatures
"""

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
    import pdb
    pdb.set_trace()
    out_iter = out.create_iter(shape)
    arr_iter = arr.create_axis_iter(shape, axis)
    if identity is not None:
        identity = identity.convert_to(dtype)
    while not out_iter.done():
        w_val = arr_iter.getitem().convert_to(dtype)
        if arr_iter.first_line:
            if identity is not None:
                w_val = func(dtype, identity, w_val)
        else:
            cur = out_iter.getitem()
            w_val = func(dtype, cur, w_val)
        out_iter.setitem(w_val)
        arr_iter.next()
        out_iter.next()
    return out
