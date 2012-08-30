
""" This file is the main run loop as well as evaluation loops for various
signatures
"""

def call2(func, name, calc_dtype, res_dtype, w_lhs, w_rhs, out):
    left_iter = w_lhs.create_iter()
    right_iter = w_rhs.create_iter()
    out_iter = out.create_iter()
    while not out_iter.done():
        w_left = left_iter.getitem().convert_to(calc_dtype)
        w_right = right_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, w_left, w_right).convert_to(
            res_dtype))
        left_iter.next()
        right_iter.next()
        out_iter.next()
    return out

def call1(func, name , calc_dtype, res_dtype, w_obj, out):
    obj_iter = w_obj.create_iter()
    out_iter = out.create_iter()
    while not out_iter.done():
        elem = obj_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, elem).convert_to(res_dtype))
        out_iter.next()
        obj_iter.next()
    return out

def setslice(target, source):
    target_iter = target.create_iter()
    dtype = target.dtype
    source_iter = source.create_iter()
    while not target_iter.done():
        target_iter.setitem(source_iter.getitem().convert_to(dtype))
        target_iter.next()
        source_iter.next()
    return target

def compute_reduce(obj, calc_dtype, func, done_func, identity):
    obj_iter = obj.create_iter()
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
    arr_iter = arr.create_iter()
    while not arr_iter.done():
        arr_iter.setitem(box)
        arr_iter.next()
