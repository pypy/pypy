
""" This file is the main run loop as well as evaluation loops for various
operations. This is the place to look for all the computations that iterate
over all the array elements.
"""

from rpython.rlib.rstring import StringBuilder
from pypy.interpreter.error import OperationError
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.micronumpy.base import W_NDimArray
from pypy.module.micronumpy.iter import PureShapeIterator
from pypy.module.micronumpy import constants
from pypy.module.micronumpy.support import int_w

call2_driver = jit.JitDriver(name='numpy_call2',
                             greens = ['shapelen', 'func', 'calc_dtype',
                                       'res_dtype'],
                             reds = ['shape', 'w_lhs', 'w_rhs', 'out',
                                     'left_iter', 'right_iter', 'out_iter'])

def call2(space, shape, func, calc_dtype, res_dtype, w_lhs, w_rhs, out):
    # handle array_priority
    # w_lhs and w_rhs could be of different ndarray subtypes. Numpy does:
    # 1. if __array_priorities__ are equal and one is an ndarray and the
    #        other is a subtype,  flip the order
    # 2. elif rhs.__array_priority__ is higher, flip the order
    # Now return the subtype of the first one

    w_ndarray = space.gettypefor(W_NDimArray)
    lhs_type = space.type(w_lhs)
    rhs_type = space.type(w_rhs)
    lhs_for_subtype = w_lhs
    rhs_for_subtype = w_rhs
    #it may be something like a FlatIter, which is not an ndarray
    if not space.is_true(space.issubtype(lhs_type, w_ndarray)):
        lhs_type = space.type(w_lhs.base)
        lhs_for_subtype = w_lhs.base
    if not space.is_true(space.issubtype(rhs_type, w_ndarray)):
        rhs_type = space.type(w_rhs.base)
        rhs_for_subtype = w_rhs.base
    if space.is_w(lhs_type, w_ndarray) and not space.is_w(rhs_type, w_ndarray):
        lhs_for_subtype = rhs_for_subtype

    # TODO handle __array_priorities__ and maybe flip the order

    if out is None:
        out = W_NDimArray.from_shape(space, shape, res_dtype,
                                     w_instance=lhs_for_subtype)
    left_iter = w_lhs.create_iter(shape)
    right_iter = w_rhs.create_iter(shape)
    out_iter = out.create_iter(shape)
    shapelen = len(shape)
    while not out_iter.done():
        call2_driver.jit_merge_point(shapelen=shapelen, func=func,
                                     calc_dtype=calc_dtype, res_dtype=res_dtype,
                                     shape=shape, w_lhs=w_lhs, w_rhs=w_rhs,
                                     out=out,
                                     left_iter=left_iter, right_iter=right_iter,
                                     out_iter=out_iter)
        w_left = left_iter.getitem().convert_to(calc_dtype)
        w_right = right_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, w_left, w_right).convert_to(
            res_dtype))
        left_iter.next()
        right_iter.next()
        out_iter.next()
    return out

call1_driver = jit.JitDriver(name='numpy_call1',
                             greens = ['shapelen', 'func', 'calc_dtype',
                                       'res_dtype'],
                             reds = ['shape', 'w_obj', 'out', 'obj_iter',
                                     'out_iter'])

def call1(space, shape, func, calc_dtype, res_dtype, w_obj, out):
    if out is None:
        out = W_NDimArray.from_shape(space, shape, res_dtype, w_instance=w_obj)
    obj_iter = w_obj.create_iter(shape)
    out_iter = out.create_iter(shape)
    shapelen = len(shape)
    while not out_iter.done():
        call1_driver.jit_merge_point(shapelen=shapelen, func=func,
                                     calc_dtype=calc_dtype, res_dtype=res_dtype,
                                     shape=shape, w_obj=w_obj, out=out,
                                     obj_iter=obj_iter, out_iter=out_iter)
        elem = obj_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, elem).convert_to(res_dtype))
        out_iter.next()
        obj_iter.next()
    return out

setslice_driver1 = jit.JitDriver(name='numpy_setslice1',
                                greens = ['shapelen', 'dtype'],
                                reds = 'auto')
setslice_driver2 = jit.JitDriver(name='numpy_setslice2',
                                greens = ['shapelen', 'dtype'],
                                reds = 'auto')

def setslice(space, shape, target, source):
    if target.dtype.is_str_or_unicode():
        return setslice_build_and_convert(space, shape, target, source)
    return setslice_to(space, shape, target, source)

def setslice_to(space, shape, target, source):
    # note that unlike everything else, target and source here are
    # array implementations, not arrays
    target_iter = target.create_iter(shape)
    source_iter = source.create_iter(shape)
    dtype = target.dtype
    shapelen = len(shape)
    while not target_iter.done():
        setslice_driver1.jit_merge_point(shapelen=shapelen, dtype=dtype)
        target_iter.setitem(source_iter.getitem().convert_to(dtype))
        target_iter.next()
        source_iter.next()
    return target

def setslice_build_and_convert(space, shape, target, source):
    # note that unlike everything else, target and source here are
    # array implementations, not arrays
    target_iter = target.create_iter(shape)
    source_iter = source.create_iter(shape)
    dtype = target.dtype
    shapelen = len(shape)
    while not target_iter.done():
        setslice_driver2.jit_merge_point(shapelen=shapelen, dtype=dtype)
        target_iter.setitem(dtype.build_and_convert(space, source_iter.getitem()))
        target_iter.next()
        source_iter.next()
    return target

reduce_driver = jit.JitDriver(name='numpy_reduce',
                              greens = ['shapelen', 'func', 'done_func',
                                        'calc_dtype'],
                              reds = 'auto')

def compute_reduce(obj, calc_dtype, func, done_func, identity):
    obj_iter = obj.create_iter()
    if identity is None:
        cur_value = obj_iter.getitem().convert_to(calc_dtype)
        obj_iter.next()
    else:
        cur_value = identity.convert_to(calc_dtype)
    shapelen = len(obj.get_shape())
    while not obj_iter.done():
        reduce_driver.jit_merge_point(shapelen=shapelen, func=func,
                                      done_func=done_func,
                                      calc_dtype=calc_dtype,
                                      )
        rval = obj_iter.getitem().convert_to(calc_dtype)
        if done_func is not None and done_func(calc_dtype, rval):
            return rval
        cur_value = func(calc_dtype, cur_value, rval)
        obj_iter.next()
    return cur_value

reduce_cum_driver = jit.JitDriver(name='numpy_reduce_cum_driver',
                                  greens = ['shapelen', 'func', 'dtype'],
                                  reds = 'auto')

def compute_reduce_cumultative(obj, out, calc_dtype, func, identity):
    obj_iter = obj.create_iter()
    out_iter = out.create_iter()
    cur_value = identity.convert_to(calc_dtype)
    shapelen = len(obj.get_shape())
    while not obj_iter.done():
        reduce_cum_driver.jit_merge_point(shapelen=shapelen, func=func,
                                          dtype=calc_dtype,
                                         )
        rval = obj_iter.getitem().convert_to(calc_dtype)
        cur_value = func(calc_dtype, cur_value, rval)
        out_iter.setitem(cur_value)
        out_iter.next()
        obj_iter.next()

def fill(arr, box):
    arr_iter = arr.create_iter()
    while not arr_iter.done():
        arr_iter.setitem(box)
        arr_iter.next()

where_driver = jit.JitDriver(name='numpy_where',
                             greens = ['shapelen', 'dtype', 'arr_dtype'],
                             reds = 'auto')

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
    shapelen = len(shape)
    while not iter.done():
        where_driver.jit_merge_point(shapelen=shapelen, dtype=dtype,
                                        arr_dtype=arr_dtype)
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

axis_reduce__driver = jit.JitDriver(name='numpy_axis_reduce',
                                    greens=['shapelen',
                                            'func', 'dtype'],
                                    reds='auto')

def do_axis_reduce(shape, func, arr, dtype, axis, out, identity, cumultative,
                   temp):
    out_iter = out.create_axis_iter(arr.get_shape(), axis, cumultative)
    if cumultative:
        temp_iter = temp.create_axis_iter(arr.get_shape(), axis, False)
    else:
        temp_iter = out_iter # hack
    arr_iter = arr.create_iter()
    if identity is not None:
        identity = identity.convert_to(dtype)
    shapelen = len(shape)
    while not out_iter.done():
        axis_reduce__driver.jit_merge_point(shapelen=shapelen, func=func,
                                            dtype=dtype)
        w_val = arr_iter.getitem().convert_to(dtype)
        if out_iter.first_line:
            if identity is not None:
                w_val = func(dtype, identity, w_val)
        else:
            cur = temp_iter.getitem()
            w_val = func(dtype, cur, w_val)
        out_iter.setitem(w_val)
        if cumultative:
            temp_iter.setitem(w_val)
            temp_iter.next()
        arr_iter.next()
        out_iter.next()
    return out


def _new_argmin_argmax(op_name):
    arg_driver = jit.JitDriver(name='numpy_' + op_name,
                               greens = ['shapelen', 'dtype'],
                               reds = 'auto')

    def argmin_argmax(arr):
        result = 0
        idx = 1
        dtype = arr.get_dtype()
        iter = arr.create_iter()
        cur_best = iter.getitem()
        iter.next()
        shapelen = len(arr.get_shape())
        while not iter.done():
            arg_driver.jit_merge_point(shapelen=shapelen, dtype=dtype,
                                      )
            w_val = iter.getitem()
            new_best = getattr(dtype.itemtype, op_name)(cur_best, w_val)
            if dtype.itemtype.ne(new_best, cur_best):
                result = idx
                cur_best = new_best
            iter.next()
            idx += 1
        return result
    return argmin_argmax
argmin = _new_argmin_argmax('min')
argmax = _new_argmin_argmax('max')

# note that shapelen == 2 always
dot_driver = jit.JitDriver(name = 'numpy_dot',
                           greens = ['dtype'],
                           reds = 'auto')

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
        dot_driver.jit_merge_point(dtype=dtype)
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
    if arr.is_scalar():
        return arr.get_dtype().itemtype.bool(arr.get_scalar_value())
    iter = arr.create_iter()
    return count_all_true_iter(iter, arr.get_shape(), arr.get_dtype())

count_all_true_iter_driver = jit.JitDriver(name = 'numpy_count',
                                      greens = ['shapelen', 'dtype'],
                                      reds = 'auto')
def count_all_true_iter(iter, shape, dtype):
    s = 0
    shapelen = len(shape)
    dtype = dtype
    while not iter.done():
        count_all_true_iter_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
        s += iter.getitem_bool()
        iter.next()
    return s


getitem_filter_driver = jit.JitDriver(name = 'numpy_getitem_bool',
                                      greens = ['shapelen', 'arr_dtype',
                                                'index_dtype'],
                                      reds = 'auto')

def getitem_filter(res, arr, index):
    res_iter = res.create_iter()
    shapelen = len(arr.get_shape())
    if shapelen > 1 and len(index.get_shape()) < 2:
        index_iter = index.create_iter(arr.get_shape(), backward_broadcast=True)
    else:
        index_iter = index.create_iter()
    arr_iter = arr.create_iter()
    arr_dtype = arr.get_dtype()
    index_dtype = index.get_dtype()
    # XXX length of shape of index as well?
    while not index_iter.done():
        getitem_filter_driver.jit_merge_point(shapelen=shapelen,
                                              index_dtype=index_dtype,
                                              arr_dtype=arr_dtype,
                                              )
        if index_iter.getitem_bool():
            res_iter.setitem(arr_iter.getitem())
            res_iter.next()
        index_iter.next()
        arr_iter.next()
    return res

setitem_filter_driver = jit.JitDriver(name = 'numpy_setitem_bool',
                                      greens = ['shapelen', 'arr_dtype',
                                                'index_dtype'],
                                      reds = 'auto')

def setitem_filter(arr, index, value, size):
    arr_iter = arr.create_iter()
    shapelen = len(arr.get_shape())
    if shapelen > 1 and len(index.get_shape()) < 2:
        index_iter = index.create_iter(arr.get_shape(), backward_broadcast=True)
    else:
        index_iter = index.create_iter()
    value_iter = value.create_iter([size])
    index_dtype = index.get_dtype()
    arr_dtype = arr.get_dtype()
    while not index_iter.done():
        setitem_filter_driver.jit_merge_point(shapelen=shapelen,
                                              index_dtype=index_dtype,
                                              arr_dtype=arr_dtype,
                                             )
        if index_iter.getitem_bool():
            arr_iter.setitem(value_iter.getitem())
            value_iter.next()
        arr_iter.next()
        index_iter.next()

flatiter_getitem_driver = jit.JitDriver(name = 'numpy_flatiter_getitem',
                                        greens = ['dtype'],
                                        reds = 'auto')

def flatiter_getitem(res, base_iter, step):
    ri = res.create_iter()
    dtype = res.get_dtype()
    while not ri.done():
        flatiter_getitem_driver.jit_merge_point(dtype=dtype)
        ri.setitem(base_iter.getitem())
        base_iter.next_skip_x(step)
        ri.next()
    return res

flatiter_setitem_driver1 = jit.JitDriver(name = 'numpy_flatiter_setitem1',
                                        greens = ['dtype'],
                                        reds = 'auto')

flatiter_setitem_driver2 = jit.JitDriver(name = 'numpy_flatiter_setitem2',
                                        greens = ['dtype'],
                                        reds = 'auto')

def flatiter_setitem(space, arr, val, start, step, length):
    dtype = arr.get_dtype()
    if dtype.is_str_or_unicode():
        return flatiter_setitem_build_and_convert(space, arr, val, start, step, length)
    return flatiter_setitem_to(space, arr, val, start, step, length)

def flatiter_setitem_to(space, arr, val, start, step, length):
    dtype = arr.get_dtype()
    arr_iter = arr.create_iter()
    val_iter = val.create_iter()
    arr_iter.next_skip_x(start)
    while length > 0:
        flatiter_setitem_driver1.jit_merge_point(dtype=dtype)
        arr_iter.setitem(val_iter.getitem().convert_to(dtype))
        # need to repeat i_nput values until all assignments are done
        arr_iter.next_skip_x(step)
        length -= 1
        val_iter.next()
        # WTF numpy?
        val_iter.reset()

def flatiter_setitem_build_and_convert(space, arr, val, start, step, length):
    dtype = arr.get_dtype()
    arr_iter = arr.create_iter()
    val_iter = val.create_iter()
    arr_iter.next_skip_x(start)
    while length > 0:
        flatiter_setitem_driver2.jit_merge_point(dtype=dtype)
        arr_iter.setitem(dtype.build_and_convert(space, val_iter.getitem()))
        # need to repeat i_nput values until all assignments are done
        arr_iter.next_skip_x(step)
        length -= 1
        val_iter.next()
        # WTF numpy?
        val_iter.reset()

fromstring_driver = jit.JitDriver(name = 'numpy_fromstring',
                                  greens = ['itemsize', 'dtype'],
                                  reds = 'auto')

def fromstring_loop(a, dtype, itemsize, s):
    i = 0
    ai = a.create_iter()
    while not ai.done():
        fromstring_driver.jit_merge_point(dtype=dtype, itemsize=itemsize)
        val = dtype.itemtype.runpack_str(s[i*itemsize:i*itemsize + itemsize])
        ai.setitem(val)
        ai.next()
        i += 1

def tostring(space, arr):
    builder = StringBuilder()
    iter = arr.create_iter()
    w_res_str = W_NDimArray.from_shape(space, [1], arr.get_dtype(), order='C')
    itemsize = arr.get_dtype().itemtype.get_element_size()
    res_str_casted = rffi.cast(rffi.CArrayPtr(lltype.Char),
                               w_res_str.implementation.get_storage_as_int(space))
    while not iter.done():
        w_res_str.implementation.setitem(0, iter.getitem())
        for i in range(itemsize):
            builder.append(res_str_casted[i])
        iter.next()
    return builder.build()

getitem_int_driver = jit.JitDriver(name = 'numpy_getitem_int',
                                   greens = ['shapelen', 'indexlen',
                                             'prefixlen', 'dtype'],
                                   reds = 'auto')

def getitem_array_int(space, arr, res, iter_shape, indexes_w, prefix_w):
    shapelen = len(iter_shape)
    prefixlen = len(prefix_w)
    indexlen = len(indexes_w)
    dtype = arr.get_dtype()
    iter = PureShapeIterator(iter_shape, indexes_w)
    indexlen = len(indexes_w)
    while not iter.done():
        getitem_int_driver.jit_merge_point(shapelen=shapelen, indexlen=indexlen,
                                           dtype=dtype, prefixlen=prefixlen)
        # prepare the index
        index_w = [None] * indexlen
        for i in range(indexlen):
            if iter.idx_w[i] is not None:
                index_w[i] = iter.idx_w[i].getitem()
            else:
                index_w[i] = indexes_w[i]
        res.descr_setitem(space, space.newtuple(prefix_w[:prefixlen] +
                                            iter.get_index(space, shapelen)),
                          arr.descr_getitem(space, space.newtuple(index_w)))
        iter.next()
    return res

setitem_int_driver = jit.JitDriver(name = 'numpy_setitem_int',
                                   greens = ['shapelen', 'indexlen',
                                             'prefixlen', 'dtype'],
                                   reds = 'auto')

def setitem_array_int(space, arr, iter_shape, indexes_w, val_arr,
                      prefix_w):
    shapelen = len(iter_shape)
    indexlen = len(indexes_w)
    prefixlen = len(prefix_w)
    dtype = arr.get_dtype()
    iter = PureShapeIterator(iter_shape, indexes_w)
    while not iter.done():
        setitem_int_driver.jit_merge_point(shapelen=shapelen, indexlen=indexlen,
                                           dtype=dtype, prefixlen=prefixlen)
        # prepare the index
        index_w = [None] * indexlen
        for i in range(indexlen):
            if iter.idx_w[i] is not None:
                index_w[i] = iter.idx_w[i].getitem()
            else:
                index_w[i] = indexes_w[i]
        w_idx = space.newtuple(prefix_w[:prefixlen] + iter.get_index(space,
                                                                  shapelen))
        arr.descr_setitem(space, space.newtuple(index_w),
                          val_arr.descr_getitem(space, w_idx))
        iter.next()

byteswap_driver = jit.JitDriver(name='numpy_byteswap_driver',
                                greens = ['dtype'],
                                reds = 'auto')

def byteswap(from_, to):
    dtype = from_.dtype
    from_iter = from_.create_iter()
    to_iter = to.create_iter()
    while not from_iter.done():
        byteswap_driver.jit_merge_point(dtype=dtype)
        to_iter.setitem(dtype.itemtype.byteswap(from_iter.getitem()))
        to_iter.next()
        from_iter.next()

choose_driver = jit.JitDriver(name='numpy_choose_driver',
                              greens = ['shapelen', 'mode', 'dtype'],
                              reds = 'auto')

def choose(space, arr, choices, shape, dtype, out, mode):
    shapelen = len(shape)
    iterators = [a.create_iter(shape) for a in choices]
    arr_iter = arr.create_iter(shape)
    out_iter = out.create_iter(shape)
    while not arr_iter.done():
        choose_driver.jit_merge_point(shapelen=shapelen, dtype=dtype,
                                      mode=mode)
        index = int_w(space, arr_iter.getitem())
        if index < 0 or index >= len(iterators):
            if mode == constants.MODE_RAISE:
                raise OperationError(space.w_ValueError, space.wrap(
                    "invalid entry in choice array"))
            elif mode == constants.MODE_WRAP:
                index = index % (len(iterators))
            else:
                assert mode == constants.MODE_CLIP
                if index < 0:
                    index = 0
                else:
                    index = len(iterators) - 1
        out_iter.setitem(iterators[index].getitem().convert_to(dtype))
        for iter in iterators:
            iter.next()
        out_iter.next()
        arr_iter.next()

clip_driver = jit.JitDriver(name='numpy_clip_driver',
                            greens = ['shapelen', 'dtype'],
                            reds = 'auto')

def clip(space, arr, shape, min, max, out):
    arr_iter = arr.create_iter(shape)
    dtype = out.get_dtype()
    shapelen = len(shape)
    min_iter = min.create_iter(shape)
    max_iter = max.create_iter(shape)
    out_iter = out.create_iter(shape)
    while not arr_iter.done():
        clip_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
        w_v = arr_iter.getitem().convert_to(dtype)
        w_min = min_iter.getitem().convert_to(dtype)
        w_max = max_iter.getitem().convert_to(dtype)
        if dtype.itemtype.lt(w_v, w_min):
            w_v = w_min
        elif dtype.itemtype.gt(w_v, w_max):
            w_v = w_max
        out_iter.setitem(w_v)
        arr_iter.next()
        max_iter.next()
        out_iter.next()
        min_iter.next()

round_driver = jit.JitDriver(name='numpy_round_driver',
                             greens = ['shapelen', 'dtype'],
                             reds = 'auto')

def round(space, arr, dtype, shape, decimals, out):
    arr_iter = arr.create_iter(shape)
    shapelen = len(shape)
    out_iter = out.create_iter(shape)
    while not arr_iter.done():
        round_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
        w_v = dtype.itemtype.round(arr_iter.getitem().convert_to(dtype),
                     decimals)
        out_iter.setitem(w_v)
        arr_iter.next()
        out_iter.next()

diagonal_simple_driver = jit.JitDriver(name='numpy_diagonal_simple_driver',
                                       greens = ['axis1', 'axis2'],
                                       reds = 'auto')

def diagonal_simple(space, arr, out, offset, axis1, axis2, size):
    out_iter = out.create_iter()
    i = 0
    index = [0] * 2
    while i < size:
        diagonal_simple_driver.jit_merge_point(axis1=axis1, axis2=axis2)
        index[axis1] = i
        index[axis2] = i + offset
        out_iter.setitem(arr.getitem_index(space, index))
        i += 1
        out_iter.next()

def diagonal_array(space, arr, out, offset, axis1, axis2, shape):
    out_iter = out.create_iter()
    iter = PureShapeIterator(shape, [])
    shapelen_minus_1 = len(shape) - 1
    assert shapelen_minus_1 >= 0
    if axis1 < axis2:
        a = axis1
        b = axis2 - 1
    else:
        a = axis2
        b = axis1 - 1
    assert a >= 0
    assert b >= 0
    while not iter.done():
        last_index = iter.indexes[-1]
        if axis1 < axis2:
            indexes = (iter.indexes[:a] + [last_index] +
                       iter.indexes[a:b] + [last_index + offset] +
                       iter.indexes[b:shapelen_minus_1])
        else:
            indexes = (iter.indexes[:a] + [last_index + offset] +
                       iter.indexes[a:b] + [last_index] +
                       iter.indexes[b:shapelen_minus_1])
        out_iter.setitem(arr.getitem_index(space, indexes))
        iter.next()
        out_iter.next()

