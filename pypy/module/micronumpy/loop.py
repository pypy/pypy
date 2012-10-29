
""" This file is the main run loop as well as evaluation loops for various
operations. This is the place to look for all the computations that iterate
over all the array elements.
"""

from pypy.rlib.rstring import StringBuilder
from pypy.rlib import jit
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.micronumpy.base import W_NDimArray
from pypy.module.micronumpy.iter import PureShapeIterator

call2_driver = jit.JitDriver(name='numpy_call2',
                             greens = ['shapelen', 'func', 'calc_dtype',
                                       'res_dtype'],
                             reds = ['shape', 'w_lhs', 'w_rhs', 'out',
                                     'left_iter', 'right_iter', 'out_iter'])

def call2(shape, func, calc_dtype, res_dtype, w_lhs, w_rhs, out):
    if out is None:
        out = W_NDimArray.from_shape(shape, res_dtype)
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

def call1(shape, func, calc_dtype, res_dtype, w_obj, out):
    if out is None:
        out = W_NDimArray.from_shape(shape, res_dtype)
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

setslice_driver = jit.JitDriver(name='numpy_setslice',
                                greens = ['shapelen', 'dtype'],
                                reds = ['target', 'source', 'target_iter',
                                        'source_iter'])

def setslice(shape, target, source):
    # note that unlike everything else, target and source here are
    # array implementations, not arrays
    target_iter = target.create_iter(shape)
    source_iter = source.create_iter(shape)
    dtype = target.dtype
    shapelen = len(shape)
    while not target_iter.done():
        setslice_driver.jit_merge_point(shapelen=shapelen, dtype=dtype,
                                        target=target, source=source,
                                        target_iter=target_iter,
                                        source_iter=source_iter)
        target_iter.setitem(source_iter.getitem().convert_to(dtype))
        target_iter.next()
        source_iter.next()
    return target

reduce_driver = jit.JitDriver(name='numpy_reduce',
                              greens = ['shapelen', 'func', 'done_func',
                                        'calc_dtype', 'identity'],
                              reds = ['obj', 'obj_iter', 'cur_value'])

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
                                      calc_dtype=calc_dtype, identity=identity,
                                      done_func=done_func, obj=obj,
                                      obj_iter=obj_iter, cur_value=cur_value)
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

where_driver = jit.JitDriver(name='numpy_where',
                             greens = ['shapelen', 'dtype', 'arr_dtype'],
                             reds = ['shape', 'arr', 'x', 'y','arr_iter', 'out',
                                     'x_iter', 'y_iter', 'iter', 'out_iter'])

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
        where_driver.jit_merge_point(shapelen=shapelen, shape=shape,
                                     dtype=dtype, iter=iter, x_iter=x_iter,
                                     y_iter=y_iter, arr_iter=arr_iter,
                                     arr=arr, x=x, y=y, arr_dtype=arr_dtype,
                                     out_iter=out_iter, out=out)
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
                                    greens=['shapelen', 'func', 'dtype',
                                            'identity'],
                                    reds=['axis', 'arr', 'out', 'shape',
                                          'out_iter', 'arr_iter'])

def do_axis_reduce(shape, func, arr, dtype, axis, out, identity):
    out_iter = out.create_axis_iter(arr.get_shape(), axis)
    arr_iter = arr.create_iter()
    if identity is not None:
        identity = identity.convert_to(dtype)
    shapelen = len(shape)
    while not out_iter.done():
        axis_reduce__driver.jit_merge_point(shapelen=shapelen, func=func,
                                            dtype=dtype, identity=identity,
                                            axis=axis, arr=arr, out=out,
                                            shape=shape, out_iter=out_iter,
                                            arr_iter=arr_iter)
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


def _new_argmin_argmax(op_name):
    arg_driver = jit.JitDriver(name='numpy_' + op_name,
                               greens = ['shapelen', 'dtype'],
                               reds = ['result', 'idx', 'cur_best', 'arr',
                                       'iter'])
    
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
                                       result=result, idx=idx,
                                       cur_best=cur_best, arr=arr, iter=iter)
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
                           reds = ['outi', 'lefti', 'righti', 'result'])

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
        dot_driver.jit_merge_point(dtype=dtype, outi=outi, lefti=lefti,
                                   righti=righti, result=result)
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

count_all_true_driver = jit.JitDriver(name = 'numpy_count',
                                      greens = ['shapelen', 'dtype'],
                                      reds = ['s', 'iter'])

def count_all_true(arr):
    s = 0
    if arr.is_scalar():
        return arr.get_dtype().itemtype.bool(arr.get_scalar_value())
    iter = arr.create_iter()
    shapelen = len(arr.get_shape())
    dtype = arr.get_dtype()
    while not iter.done():
        count_all_true_driver.jit_merge_point(shapelen=shapelen, iter=iter,
                                              s=s, dtype=dtype)
        s += iter.getitem_bool()
        iter.next()
    return s

getitem_filter_driver = jit.JitDriver(name = 'numpy_getitem_bool',
                                      greens = ['shapelen', 'arr_dtype',
                                                'index_dtype'],
                                      reds = ['res', 'index_iter', 'res_iter',
                                              'arr_iter'])

def getitem_filter(res, arr, index):
    res_iter = res.create_iter()
    index_iter = index.create_iter()
    arr_iter = arr.create_iter()
    shapelen = len(arr.get_shape())
    arr_dtype = arr.get_dtype()
    index_dtype = index.get_dtype()
    # XXX length of shape of index as well?
    while not index_iter.done():
        getitem_filter_driver.jit_merge_point(shapelen=shapelen,
                                              index_dtype=index_dtype,
                                              arr_dtype=arr_dtype,
                                              res=res, index_iter=index_iter,
                                              res_iter=res_iter,
                                              arr_iter=arr_iter)
        if index_iter.getitem_bool():
            res_iter.setitem(arr_iter.getitem())
            res_iter.next()
        index_iter.next()
        arr_iter.next()
    return res

setitem_filter_driver = jit.JitDriver(name = 'numpy_setitem_bool',
                                      greens = ['shapelen', 'arr_dtype',
                                                'index_dtype'],
                                      reds = ['index_iter', 'value_iter',
                                              'arr_iter'])

def setitem_filter(arr, index, value):
    arr_iter = arr.create_iter()
    index_iter = index.create_iter()
    value_iter = value.create_iter()
    shapelen = len(arr.get_shape())
    index_dtype = index.get_dtype()
    arr_dtype = arr.get_dtype()
    while not index_iter.done():
        setitem_filter_driver.jit_merge_point(shapelen=shapelen,
                                              index_dtype=index_dtype,
                                              arr_dtype=arr_dtype,
                                              index_iter=index_iter,
                                              value_iter=value_iter,
                                              arr_iter=arr_iter)
        if index_iter.getitem_bool():
            arr_iter.setitem(value_iter.getitem())
            value_iter.next()
        arr_iter.next()
        index_iter.next()

flatiter_getitem_driver = jit.JitDriver(name = 'numpy_flatiter_getitem',
                                        greens = ['dtype'],
                                        reds = ['step', 'ri', 'res',
                                                'base_iter'])

def flatiter_getitem(res, base_iter, step):
    ri = res.create_iter()
    dtype = res.get_dtype()
    while not ri.done():
        flatiter_getitem_driver.jit_merge_point(dtype=dtype,
                                                base_iter=base_iter,
                                                ri=ri, res=res, step=step)
        ri.setitem(base_iter.getitem())
        base_iter.next_skip_x(step)
        ri.next()
    return res

flatiter_setitem_driver = jit.JitDriver(name = 'numpy_flatiter_setitem',
                                        greens = ['dtype'],
                                        reds = ['length', 'step', 'arr_iter',
                                                'val_iter'])

def flatiter_setitem(arr, val, start, step, length):
    dtype = arr.get_dtype()
    arr_iter = arr.create_iter()
    val_iter = val.create_iter()
    arr_iter.next_skip_x(start)
    while length > 0:
        flatiter_setitem_driver.jit_merge_point(dtype=dtype, length=length,
                                                step=step, arr_iter=arr_iter,
                                                val_iter=val_iter)
        arr_iter.setitem(val_iter.getitem().convert_to(dtype))
        # need to repeat i_nput values until all assignments are done
        arr_iter.next_skip_x(step)
        length -= 1
        val_iter.next()
        # WTF numpy?
        val_iter.reset()

fromstring_driver = jit.JitDriver(name = 'numpy_fromstring',
                                  greens = ['itemsize', 'dtype'],
                                  reds = ['i', 's', 'ai'])

def fromstring_loop(a, dtype, itemsize, s):
    i = 0
    ai = a.create_iter()
    while not ai.done():
        fromstring_driver.jit_merge_point(dtype=dtype, s=s, ai=ai, i=i,
                                          itemsize=itemsize)
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

getitem_int_driver = jit.JitDriver(name = 'numpy_getitem_int',
                                   greens = ['shapelen', 'indexlen',
                                             'prefixlen', 'dtype'],
                                   reds = ['arr', 'res', 'iter', 'indexes_w',
                                           'prefix_w'])

def getitem_array_int(space, arr, res, iter_shape, indexes_w, prefix_w):
    shapelen = len(iter_shape)
    prefixlen = len(prefix_w)
    indexlen = len(indexes_w)
    dtype = arr.get_dtype()
    iter = PureShapeIterator(iter_shape, indexes_w)
    indexlen = len(indexes_w)
    while not iter.done():
        getitem_int_driver.jit_merge_point(shapelen=shapelen, indexlen=indexlen,
                                           dtype=dtype, arr=arr, res=res,
                                           iter=iter, indexes_w=indexes_w,
                                           prefix_w=prefix_w,
                                           prefixlen=prefixlen)
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
                                   reds = ['arr', 'iter', 'indexes_w',
                                           'prefix_w', 'val_arr'])

def setitem_array_int(space, arr, iter_shape, indexes_w, val_arr,
                      prefix_w):
    shapelen = len(iter_shape)
    indexlen = len(indexes_w)
    prefixlen = len(prefix_w)
    dtype = arr.get_dtype()
    iter = PureShapeIterator(iter_shape, indexes_w)
    while not iter.done():
        setitem_int_driver.jit_merge_point(shapelen=shapelen, indexlen=indexlen,
                                           dtype=dtype, arr=arr,
                                           iter=iter, indexes_w=indexes_w,
                                           prefix_w=prefix_w, val_arr=val_arr,
                                           prefixlen=prefixlen)
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

copy_from_to_driver = jit.JitDriver(greens = ['dtype'],
                                    reds = ['from_iter', 'to_iter'])

def copy_from_to(from_, to, dtype):
    from_iter = from_.create_iter()
    to_iter = to.create_iter()
    while not from_iter.done():
        copy_from_to_driver.jit_merge_point(dtype=dtype, from_iter=from_iter,
                                            to_iter=to_iter)
        to_iter.setitem(from_iter.getitem().convert_to(dtype))
        to_iter.next()
        from_iter.next()

byteswap_driver = jit.JitDriver(greens = ['dtype'],
                                reds = ['from_iter', 'to_iter'])

def byteswap(from_, to):
    dtype = from_.dtype
    from_iter = from_.create_iter()
    to_iter = to.create_iter()
    while not from_iter.done():
        byteswap_driver.jit_merge_point(dtype=dtype, from_iter=from_iter,
                                        to_iter=to_iter)
        to_iter.setitem(dtype.itemtype.byteswap(from_iter.getitem()))
        to_iter.next()
        from_iter.next()
