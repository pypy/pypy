""" This file is the main run loop as well as evaluation loops for various
operations. This is the place to look for all the computations that iterate
over all the array elements.
"""
from pypy.interpreter.error import OperationError
from rpython.rlib import jit
from rpython.rlib.rstring import StringBuilder
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.micronumpy import support, constants as NPY
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy.iterators import PureShapeIter, AxisIter, \
    AllButAxisIter
from pypy.interpreter.argument import Arguments


call2_driver = jit.JitDriver(
    name='numpy_call2',
    greens=['shapelen', 'func', 'calc_dtype', 'res_dtype'],
    reds='auto')

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

    if w_lhs.get_size() == 1:
        w_left = w_lhs.get_scalar_value().convert_to(space, calc_dtype)
        left_iter = left_state = None
    else:
        w_left = None
        left_iter, left_state = w_lhs.create_iter(shape)
        left_iter.track_index = False

    if w_rhs.get_size() == 1:
        w_right = w_rhs.get_scalar_value().convert_to(space, calc_dtype)
        right_iter = right_state = None
    else:
        w_right = None
        right_iter, right_state = w_rhs.create_iter(shape)
        right_iter.track_index = False

    if out is None:
        out = W_NDimArray.from_shape(space, shape, res_dtype,
                                     w_instance=lhs_for_subtype)
    out_iter, out_state = out.create_iter(shape)
    shapelen = len(shape)
    while not out_iter.done(out_state):
        call2_driver.jit_merge_point(shapelen=shapelen, func=func,
                                     calc_dtype=calc_dtype, res_dtype=res_dtype)
        if left_iter:
            w_left = left_iter.getitem(left_state).convert_to(space, calc_dtype)
            left_state = left_iter.next(left_state)
        if right_iter:
            w_right = right_iter.getitem(right_state).convert_to(space, calc_dtype)
            right_state = right_iter.next(right_state)
        out_iter.setitem(out_state, func(calc_dtype, w_left, w_right).convert_to(
            space, res_dtype))
        out_state = out_iter.next(out_state)
    return out

call1_driver = jit.JitDriver(
    name='numpy_call1',
    greens=['shapelen', 'func', 'calc_dtype', 'res_dtype'],
    reds='auto')

def call1(space, shape, func, calc_dtype, res_dtype, w_obj, out):
    obj_iter, obj_state = w_obj.create_iter(shape)
    obj_iter.track_index = False

    if out is None:
        out = W_NDimArray.from_shape(space, shape, res_dtype, w_instance=w_obj)
    out_iter, out_state = out.create_iter(shape)
    shapelen = len(shape)
    while not out_iter.done(out_state):
        call1_driver.jit_merge_point(shapelen=shapelen, func=func,
                                     calc_dtype=calc_dtype, res_dtype=res_dtype)
        elem = obj_iter.getitem(obj_state).convert_to(space, calc_dtype)
        out_iter.setitem(out_state, func(calc_dtype, elem).convert_to(space, res_dtype))
        out_state = out_iter.next(out_state)
        obj_state = obj_iter.next(obj_state)
    return out

call_many_to_one_driver = jit.JitDriver(
    name='numpy_call_many_to_one',
    greens=['shapelen', 'nin', 'func', 'res_dtype'],
    reds='auto')

def call_many_to_one(space, shape, func, res_dtype, in_args, out):
    # out must hav been built. func needs no calc_type, is usually an
    # external ufunc
    nin = len(in_args)
    in_iters = [None] * nin
    in_states = [None] * nin
    for i in range(nin):
        in_i = in_args[i]
        assert isinstance(in_i, W_NDimArray)
        in_iter, in_state = in_i.create_iter(shape)
        in_iters[i] = in_iter
        in_states[i] = in_state
    shapelen = len(shape)
    assert isinstance(out, W_NDimArray)
    out_iter, out_state = out.create_iter(shape)
    vals = [None] * nin
    while not out_iter.done(out_state):
        call_many_to_one_driver.jit_merge_point(shapelen=shapelen, func=func,
                                     res_dtype=res_dtype, nin=nin)
        for i in range(nin):
            vals[i] = in_iters[i].getitem(in_states[i])
        w_arglist = space.newlist(vals)
        w_out_val = space.call_args(func, Arguments.frompacked(space, w_arglist))
        out_iter.setitem(out_state, res_dtype.coerce(space, w_out_val))
        for i in range(nin):
            in_states[i] = in_iters[i].next(in_states[i])
        out_state = out_iter.next(out_state)
    return out

call_many_to_many_driver = jit.JitDriver(
    name='numpy_call_many_to_many',
    greens=['shapelen', 'nin', 'nout', 'func', 'res_dtype'],
    reds='auto')

def call_many_to_many(space, shape, func, res_dtype, in_args, out_args):
    # out must hav been built. func needs no calc_type, is usually an
    # external ufunc
    nin = len(in_args)
    in_iters = [None] * nin
    in_states = [None] * nin
    nout = len(out_args)
    out_iters = [None] * nout
    out_states = [None] * nout
    for i in range(nin):
        in_i = in_args[i]
        assert isinstance(in_i, W_NDimArray)
        in_iter, in_state = in_i.create_iter(shape)
        in_iters[i] = in_iter
        in_states[i] = in_state
    for i in range(nout):
        out_i = out_args[i]
        assert isinstance(out_i, W_NDimArray)
        out_iter, out_state = out_i.create_iter(shape)
        out_iters[i] = out_iter
        out_states[i] = out_state
    shapelen = len(shape)
    vals = [None] * nin
    while not out_iters[0].done(out_states[0]):
        call_many_to_many_driver.jit_merge_point(shapelen=shapelen, func=func,
                                     res_dtype=res_dtype, nin=nin, nout=nout)
        for i in range(nin):
            vals[i] = in_iters[i].getitem(in_states[i])
        w_arglist = space.newlist(vals)
        w_outvals = space.call_args(func, Arguments.frompacked(space, w_arglist))
        # w_outvals should be a tuple, but func can return a single value as well 
        if space.isinstance_w(w_outvals, space.w_tuple):
            batch = space.listview(w_outvals)
            for i in range(len(batch)):
                out_iters[i].setitem(out_states[i], res_dtype.coerce(space, batch[i]))
                out_states[i] = out_iters[i].next(out_states[i])
        else:
            out_iters[0].setitem(out_states[0], res_dtype.coerce(space, w_outvals))
            out_states[0] = out_iters[0].next(out_states[0])
        for i in range(nin):
            in_states[i] = in_iters[i].next(in_states[i])
    return space.newtuple([convert_to_array(space, o) for o in out_args])

setslice_driver = jit.JitDriver(name='numpy_setslice',
                                greens = ['shapelen', 'dtype'],
                                reds = 'auto')

def setslice(space, shape, target, source):
    if not shape:
        dtype = target.dtype
        val = source.getitem(source.start)
        if dtype.is_str_or_unicode():
            val = dtype.coerce(space, val)
        else:
            val = val.convert_to(space, dtype)
        target.setitem(target.start, val)
        return target
    return _setslice(space, shape, target, source)

def _setslice(space, shape, target, source):
    # note that unlike everything else, target and source here are
    # array implementations, not arrays
    target_iter, target_state = target.create_iter(shape)
    source_iter, source_state = source.create_iter(shape)
    source_iter.track_index = False
    dtype = target.dtype
    shapelen = len(shape)
    while not target_iter.done(target_state):
        setslice_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
        val = source_iter.getitem(source_state)
        if dtype.is_str_or_unicode():
            val = dtype.coerce(space, val)
        else:
            val = val.convert_to(space, dtype)
        target_iter.setitem(target_state, val)
        target_state = target_iter.next(target_state)
        source_state = source_iter.next(source_state)
    return target

reduce_driver = jit.JitDriver(name='numpy_reduce',
                              greens = ['shapelen', 'func', 'done_func',
                                        'calc_dtype'],
                              reds = 'auto')

def compute_reduce(space, obj, calc_dtype, func, done_func, identity):
    obj_iter, obj_state = obj.create_iter()
    if identity is None:
        cur_value = obj_iter.getitem(obj_state).convert_to(space, calc_dtype)
        obj_state = obj_iter.next(obj_state)
    else:
        cur_value = identity.convert_to(space, calc_dtype)
    shapelen = len(obj.get_shape())
    while not obj_iter.done(obj_state):
        reduce_driver.jit_merge_point(shapelen=shapelen, func=func,
                                      done_func=done_func,
                                      calc_dtype=calc_dtype)
        rval = obj_iter.getitem(obj_state).convert_to(space, calc_dtype)
        if done_func is not None and done_func(calc_dtype, rval):
            return rval
        cur_value = func(calc_dtype, cur_value, rval)
        obj_state = obj_iter.next(obj_state)
    return cur_value

reduce_cum_driver = jit.JitDriver(name='numpy_reduce_cum_driver',
                                  greens = ['shapelen', 'func', 'dtype'],
                                  reds = 'auto')

def compute_reduce_cumulative(space, obj, out, calc_dtype, func, identity):
    obj_iter, obj_state = obj.create_iter()
    out_iter, out_state = out.create_iter()
    out_iter.track_index = False
    if identity is None:
        cur_value = obj_iter.getitem(obj_state).convert_to(space, calc_dtype)
        out_iter.setitem(out_state, cur_value)
        out_state = out_iter.next(out_state)
        obj_state = obj_iter.next(obj_state)
    else:
        cur_value = identity.convert_to(space, calc_dtype)
    shapelen = len(obj.get_shape())
    while not obj_iter.done(obj_state):
        reduce_cum_driver.jit_merge_point(shapelen=shapelen, func=func,
                                          dtype=calc_dtype)
        rval = obj_iter.getitem(obj_state).convert_to(space, calc_dtype)
        cur_value = func(calc_dtype, cur_value, rval)
        out_iter.setitem(out_state, cur_value)
        out_state = out_iter.next(out_state)
        obj_state = obj_iter.next(obj_state)

def fill(arr, box):
    arr_iter, arr_state = arr.create_iter()
    while not arr_iter.done(arr_state):
        arr_iter.setitem(arr_state, box)
        arr_state = arr_iter.next(arr_state)

def assign(space, arr, seq):
    arr_iter, arr_state = arr.create_iter()
    arr_dtype = arr.get_dtype()
    for item in seq:
        arr_iter.setitem(arr_state, arr_dtype.coerce(space, item))
        arr_state = arr_iter.next(arr_state)

where_driver = jit.JitDriver(name='numpy_where',
                             greens = ['shapelen', 'dtype', 'arr_dtype'],
                             reds = 'auto')

def where(space, out, shape, arr, x, y, dtype):
    out_iter, out_state = out.create_iter(shape)
    arr_iter, arr_state = arr.create_iter(shape)
    arr_dtype = arr.get_dtype()
    x_iter, x_state = x.create_iter(shape)
    y_iter, y_state = y.create_iter(shape)
    if x.is_scalar():
        if y.is_scalar():
            iter, state = arr_iter, arr_state
        else:
            iter, state = y_iter, y_state
    else:
        iter, state = x_iter, x_state
    out_iter.track_index = x_iter.track_index = False
    arr_iter.track_index = y_iter.track_index = False
    iter.track_index = True
    shapelen = len(shape)
    while not iter.done(state):
        where_driver.jit_merge_point(shapelen=shapelen, dtype=dtype,
                                        arr_dtype=arr_dtype)
        w_cond = arr_iter.getitem(arr_state)
        if arr_dtype.itemtype.bool(w_cond):
            w_val = x_iter.getitem(x_state).convert_to(space, dtype)
        else:
            w_val = y_iter.getitem(y_state).convert_to(space, dtype)
        out_iter.setitem(out_state, w_val)
        out_state = out_iter.next(out_state)
        arr_state = arr_iter.next(arr_state)
        x_state = x_iter.next(x_state)
        y_state = y_iter.next(y_state)
        if x.is_scalar():
            if y.is_scalar():
                state = arr_state
            else:
                state = y_state
        else:
            state = x_state
    return out

axis_reduce_driver = jit.JitDriver(name='numpy_axis_reduce',
                                   greens=['shapelen', 'func', 'dtype'],
                                   reds='auto')

def do_axis_reduce(space, shape, func, arr, dtype, axis, out, identity, cumulative,
                   temp):
    out_iter = AxisIter(out.implementation, arr.get_shape(), axis, cumulative)
    out_state = out_iter.reset()
    if cumulative:
        temp_iter = AxisIter(temp.implementation, arr.get_shape(), axis, False)
        temp_state = temp_iter.reset()
    else:
        temp_iter = out_iter  # hack
        temp_state = out_state
    arr_iter, arr_state = arr.create_iter()
    arr_iter.track_index = False
    if identity is not None:
        identity = identity.convert_to(space, dtype)
    shapelen = len(shape)
    while not out_iter.done(out_state):
        axis_reduce_driver.jit_merge_point(shapelen=shapelen, func=func,
                                           dtype=dtype)
        w_val = arr_iter.getitem(arr_state).convert_to(space, dtype)
        arr_state = arr_iter.next(arr_state)

        out_indices = out_iter.indices(out_state)
        if out_indices[axis] == 0:
            if identity is not None:
                w_val = func(dtype, identity, w_val)
        else:
            cur = temp_iter.getitem(temp_state)
            w_val = func(dtype, cur, w_val)

        out_iter.setitem(out_state, w_val)
        out_state = out_iter.next(out_state)
        if cumulative:
            temp_iter.setitem(temp_state, w_val)
            temp_state = temp_iter.next(temp_state)
        else:
            temp_state = out_state
    return out


def _new_argmin_argmax(op_name):
    arg_driver = jit.JitDriver(name='numpy_' + op_name,
                               greens = ['shapelen', 'dtype'],
                               reds = 'auto')

    def argmin_argmax(arr):
        result = 0
        idx = 1
        dtype = arr.get_dtype()
        iter, state = arr.create_iter()
        cur_best = iter.getitem(state)
        state = iter.next(state)
        shapelen = len(arr.get_shape())
        while not iter.done(state):
            arg_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
            w_val = iter.getitem(state)
            new_best = getattr(dtype.itemtype, op_name)(cur_best, w_val)
            if dtype.itemtype.ne(new_best, cur_best):
                result = idx
                cur_best = new_best
            state = iter.next(state)
            idx += 1
        return result
    return argmin_argmax
argmin = _new_argmin_argmax('min')
argmax = _new_argmin_argmax('max')

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
    left_impl = left.implementation
    right_impl = right.implementation
    assert left_shape[-1] == right_shape[right_critical_dim]
    assert result.get_dtype() == dtype
    outi, outs = result.create_iter()
    outi.track_index = False
    lefti = AllButAxisIter(left_impl, len(left_shape) - 1)
    righti = AllButAxisIter(right_impl, right_critical_dim)
    lefts = lefti.reset()
    rights = righti.reset()
    n = left_impl.shape[-1]
    s1 = left_impl.strides[-1]
    s2 = right_impl.strides[right_critical_dim]
    while not lefti.done(lefts):
        while not righti.done(rights):
            oval = outi.getitem(outs)
            i1 = lefts.offset
            i2 = rights.offset
            i = 0
            while i < n:
                i += 1
                dot_driver.jit_merge_point(dtype=dtype)
                lval = left_impl.getitem(i1).convert_to(space, dtype)
                rval = right_impl.getitem(i2).convert_to(space, dtype)
                oval = dtype.itemtype.add(oval, dtype.itemtype.mul(lval, rval))
                i1 += s1
                i2 += s2
            outi.setitem(outs, oval)
            outs = outi.next(outs)
            rights = righti.next(rights)
        rights = righti.reset(rights)
        lefts = lefti.next(lefts)
    return result

count_all_true_driver = jit.JitDriver(name = 'numpy_count',
                                      greens = ['shapelen', 'dtype'],
                                      reds = 'auto')

def count_all_true_concrete(impl):
    s = 0
    iter, state = impl.create_iter()
    shapelen = len(impl.shape)
    dtype = impl.dtype
    while not iter.done(state):
        count_all_true_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
        s += iter.getitem_bool(state)
        state = iter.next(state)
    return s

def count_all_true(arr):
    if arr.is_scalar():
        return arr.get_dtype().itemtype.bool(arr.get_scalar_value())
    else:
        return count_all_true_concrete(arr.implementation)

nonzero_driver = jit.JitDriver(name = 'numpy_nonzero',
                               greens = ['shapelen', 'dims', 'dtype'],
                               reds = 'auto')

def nonzero(res, arr, box):
    res_iter, res_state = res.create_iter()
    arr_iter, arr_state = arr.create_iter()
    shapelen = len(arr.shape)
    dtype = arr.dtype
    dims = range(shapelen)
    while not arr_iter.done(arr_state):
        nonzero_driver.jit_merge_point(shapelen=shapelen, dims=dims, dtype=dtype)
        if arr_iter.getitem_bool(arr_state):
            arr_indices = arr_iter.indices(arr_state)
            for d in dims:
                res_iter.setitem(res_state, box(arr_indices[d]))
                res_state = res_iter.next(res_state)
        arr_state = arr_iter.next(arr_state)
    return res


getitem_filter_driver = jit.JitDriver(name = 'numpy_getitem_bool',
                                      greens = ['shapelen', 'arr_dtype',
                                                'index_dtype'],
                                      reds = 'auto')

def getitem_filter(res, arr, index):
    res_iter, res_state = res.create_iter()
    shapelen = len(arr.get_shape())
    if shapelen > 1 and len(index.get_shape()) < 2:
        index_iter, index_state = index.create_iter(arr.get_shape(), backward_broadcast=True)
    else:
        index_iter, index_state = index.create_iter()
    arr_iter, arr_state = arr.create_iter()
    arr_dtype = arr.get_dtype()
    index_dtype = index.get_dtype()
    # XXX length of shape of index as well?
    while not index_iter.done(index_state):
        getitem_filter_driver.jit_merge_point(shapelen=shapelen,
                                              index_dtype=index_dtype,
                                              arr_dtype=arr_dtype,
                                              )
        if index_iter.getitem_bool(index_state):
            res_iter.setitem(res_state, arr_iter.getitem(arr_state))
            res_state = res_iter.next(res_state)
        index_state = index_iter.next(index_state)
        arr_state = arr_iter.next(arr_state)
    return res

setitem_filter_driver = jit.JitDriver(name = 'numpy_setitem_bool',
                                      greens = ['shapelen', 'arr_dtype',
                                                'index_dtype'],
                                      reds = 'auto')

def setitem_filter(space, arr, index, value):
    arr_iter, arr_state = arr.create_iter()
    shapelen = len(arr.get_shape())
    if shapelen > 1 and len(index.get_shape()) < 2:
        index_iter, index_state = index.create_iter(arr.get_shape(), backward_broadcast=True)
    else:
        index_iter, index_state = index.create_iter()
    if value.get_size() == 1:
        value_iter, value_state = value.create_iter(arr.get_shape())
    else:
        value_iter, value_state = value.create_iter()
    index_dtype = index.get_dtype()
    arr_dtype = arr.get_dtype()
    while not index_iter.done(index_state):
        setitem_filter_driver.jit_merge_point(shapelen=shapelen,
                                              index_dtype=index_dtype,
                                              arr_dtype=arr_dtype,
                                             )
        if index_iter.getitem_bool(index_state):
            val = arr_dtype.coerce(space, value_iter.getitem(value_state))
            value_state = value_iter.next(value_state)
            arr_iter.setitem(arr_state, val)
        arr_state = arr_iter.next(arr_state)
        index_state = index_iter.next(index_state)

flatiter_getitem_driver = jit.JitDriver(name = 'numpy_flatiter_getitem',
                                        greens = ['dtype'],
                                        reds = 'auto')

def flatiter_getitem(res, base_iter, base_state, step):
    ri, rs = res.create_iter()
    dtype = res.get_dtype()
    while not ri.done(rs):
        flatiter_getitem_driver.jit_merge_point(dtype=dtype)
        ri.setitem(rs, base_iter.getitem(base_state))
        base_state = base_iter.goto(base_state.index + step)
        rs = ri.next(rs)
    return res

flatiter_setitem_driver = jit.JitDriver(name = 'numpy_flatiter_setitem',
                                        greens = ['dtype'],
                                        reds = 'auto')

def flatiter_setitem(space, dtype, val, arr_iter, arr_state, step, length):
    val_iter, val_state = val.create_iter()
    while length > 0:
        flatiter_setitem_driver.jit_merge_point(dtype=dtype)
        val = val_iter.getitem(val_state)
        if dtype.is_str_or_unicode():
            val = dtype.coerce(space, val)
        else:
            val = val.convert_to(space, dtype)
        arr_iter.setitem(arr_state, val)
        arr_state = arr_iter.goto(arr_state.index + step)
        val_state = val_iter.next(val_state)
        if val_iter.done(val_state):
            val_state = val_iter.reset(val_state)
        length -= 1

fromstring_driver = jit.JitDriver(name = 'numpy_fromstring',
                                  greens = ['itemsize', 'dtype'],
                                  reds = 'auto')

def fromstring_loop(space, a, dtype, itemsize, s):
    i = 0
    ai, state = a.create_iter()
    while not ai.done(state):
        fromstring_driver.jit_merge_point(dtype=dtype, itemsize=itemsize)
        sub = s[i*itemsize:i*itemsize + itemsize]
        if dtype.is_str_or_unicode():
            val = dtype.coerce(space, space.wrap(sub))
        else:
            val = dtype.itemtype.runpack_str(space, sub)
        ai.setitem(state, val)
        state = ai.next(state)
        i += 1

def tostring(space, arr):
    builder = StringBuilder()
    iter, state = arr.create_iter()
    w_res_str = W_NDimArray.from_shape(space, [1], arr.get_dtype(), order='C')
    itemsize = arr.get_dtype().elsize
    res_str_casted = rffi.cast(rffi.CArrayPtr(lltype.Char),
                               w_res_str.implementation.get_storage_as_int(space))
    while not iter.done(state):
        w_res_str.implementation.setitem(0, iter.getitem(state))
        for i in range(itemsize):
            builder.append(res_str_casted[i])
        state = iter.next(state)
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
    iter = PureShapeIter(iter_shape, indexes_w)
    indexlen = len(indexes_w)
    while not iter.done():
        getitem_int_driver.jit_merge_point(shapelen=shapelen, indexlen=indexlen,
                                           dtype=dtype, prefixlen=prefixlen)
        # prepare the index
        index_w = [None] * indexlen
        for i in range(indexlen):
            if iter.idx_w_i[i] is not None:
                index_w[i] = iter.idx_w_i[i].getitem(iter.idx_w_s[i])
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
    iter = PureShapeIter(iter_shape, indexes_w)
    while not iter.done():
        setitem_int_driver.jit_merge_point(shapelen=shapelen, indexlen=indexlen,
                                           dtype=dtype, prefixlen=prefixlen)
        # prepare the index
        index_w = [None] * indexlen
        for i in range(indexlen):
            if iter.idx_w_i[i] is not None:
                index_w[i] = iter.idx_w_i[i].getitem(iter.idx_w_s[i])
            else:
                index_w[i] = indexes_w[i]
        w_idx = space.newtuple(prefix_w[:prefixlen] + iter.get_index(space,
                                                                  shapelen))
        if val_arr.is_scalar():
            w_value = val_arr.get_scalar_value()
        else:
            w_value = val_arr.descr_getitem(space, w_idx)
        arr.descr_setitem(space, space.newtuple(index_w), w_value)
        iter.next()

byteswap_driver = jit.JitDriver(name='numpy_byteswap_driver',
                                greens = ['dtype'],
                                reds = 'auto')

def byteswap(from_, to):
    dtype = from_.dtype
    from_iter, from_state = from_.create_iter()
    to_iter, to_state = to.create_iter()
    while not from_iter.done(from_state):
        byteswap_driver.jit_merge_point(dtype=dtype)
        val = dtype.itemtype.byteswap(from_iter.getitem(from_state))
        to_iter.setitem(to_state, val)
        to_state = to_iter.next(to_state)
        from_state = from_iter.next(from_state)

choose_driver = jit.JitDriver(name='numpy_choose_driver',
                              greens = ['shapelen', 'mode', 'dtype'],
                              reds = 'auto')

def choose(space, arr, choices, shape, dtype, out, mode):
    shapelen = len(shape)
    pairs = [a.create_iter(shape) for a in choices]
    iterators = [i[0] for i in pairs]
    states = [i[1] for i in pairs]
    arr_iter, arr_state = arr.create_iter(shape)
    out_iter, out_state = out.create_iter(shape)
    while not arr_iter.done(arr_state):
        choose_driver.jit_merge_point(shapelen=shapelen, dtype=dtype,
                                      mode=mode)
        index = support.index_w(space, arr_iter.getitem(arr_state))
        if index < 0 or index >= len(iterators):
            if mode == NPY.RAISE:
                raise OperationError(space.w_ValueError, space.wrap(
                    "invalid entry in choice array"))
            elif mode == NPY.WRAP:
                index = index % (len(iterators))
            else:
                assert mode == NPY.CLIP
                if index < 0:
                    index = 0
                else:
                    index = len(iterators) - 1
        val = iterators[index].getitem(states[index]).convert_to(space, dtype)
        out_iter.setitem(out_state, val)
        for i in range(len(iterators)):
            states[i] = iterators[i].next(states[i])
        out_state = out_iter.next(out_state)
        arr_state = arr_iter.next(arr_state)

clip_driver = jit.JitDriver(name='numpy_clip_driver',
                            greens = ['shapelen', 'dtype'],
                            reds = 'auto')

def clip(space, arr, shape, min, max, out):
    assert min or max
    arr_iter, arr_state = arr.create_iter(shape)
    if min is not None:
        min_iter, min_state = min.create_iter(shape)
    else:
        min_iter, min_state = None, None
    if max is not None:
        max_iter, max_state = max.create_iter(shape)
    else:
        max_iter, max_state = None, None
    out_iter, out_state = out.create_iter(shape)
    shapelen = len(shape)
    dtype = out.get_dtype()
    while not arr_iter.done(arr_state):
        clip_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
        w_v = arr_iter.getitem(arr_state).convert_to(space, dtype)
        arr_state = arr_iter.next(arr_state)
        if min_iter is not None:
            w_min = min_iter.getitem(min_state).convert_to(space, dtype)
            if dtype.itemtype.lt(w_v, w_min):
                w_v = w_min
            min_state = min_iter.next(min_state)
        if max_iter is not None:
            w_max = max_iter.getitem(max_state).convert_to(space, dtype)
            if dtype.itemtype.gt(w_v, w_max):
                w_v = w_max
            max_state = max_iter.next(max_state)
        out_iter.setitem(out_state, w_v)
        out_state = out_iter.next(out_state)

round_driver = jit.JitDriver(name='numpy_round_driver',
                             greens = ['shapelen', 'dtype'],
                             reds = 'auto')

def round(space, arr, dtype, shape, decimals, out):
    arr_iter, arr_state = arr.create_iter(shape)
    out_iter, out_state = out.create_iter(shape)
    shapelen = len(shape)
    while not arr_iter.done(arr_state):
        round_driver.jit_merge_point(shapelen=shapelen, dtype=dtype)
        w_v = arr_iter.getitem(arr_state).convert_to(space, dtype)
        w_v = dtype.itemtype.round(w_v, decimals)
        out_iter.setitem(out_state, w_v)
        arr_state = arr_iter.next(arr_state)
        out_state = out_iter.next(out_state)

diagonal_simple_driver = jit.JitDriver(name='numpy_diagonal_simple_driver',
                                       greens = ['axis1', 'axis2'],
                                       reds = 'auto')

def diagonal_simple(space, arr, out, offset, axis1, axis2, size):
    out_iter, out_state = out.create_iter()
    i = 0
    index = [0] * 2
    while i < size:
        diagonal_simple_driver.jit_merge_point(axis1=axis1, axis2=axis2)
        index[axis1] = i
        index[axis2] = i + offset
        out_iter.setitem(out_state, arr.getitem_index(space, index))
        i += 1
        out_state = out_iter.next(out_state)

def diagonal_array(space, arr, out, offset, axis1, axis2, shape):
    out_iter, out_state = out.create_iter()
    iter = PureShapeIter(shape, [])
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
        out_iter.setitem(out_state, arr.getitem_index(space, indexes))
        iter.next()
        out_state = out_iter.next(out_state)

def _new_binsearch(side, op_name):
    binsearch_driver = jit.JitDriver(name='numpy_binsearch_' + side,
                                     greens=['dtype'],
                                     reds='auto')

    def binsearch(space, arr, key, ret):
        assert len(arr.get_shape()) == 1
        dtype = key.get_dtype()
        op = getattr(dtype.itemtype, op_name)
        key_iter, key_state = key.create_iter()
        ret_iter, ret_state = ret.create_iter()
        ret_iter.track_index = False
        size = arr.get_size()
        min_idx = 0
        max_idx = size
        last_key_val = key_iter.getitem(key_state)
        while not key_iter.done(key_state):
            key_val = key_iter.getitem(key_state)
            if dtype.itemtype.lt(last_key_val, key_val):
                max_idx = size
            else:
                min_idx = 0
                max_idx = max_idx + 1 if max_idx < size else size
            last_key_val = key_val
            while min_idx < max_idx:
                binsearch_driver.jit_merge_point(dtype=dtype)
                mid_idx = min_idx + ((max_idx - min_idx) >> 1)
                mid_val = arr.getitem(space, [mid_idx]).convert_to(space, dtype)
                if op(mid_val, key_val):
                    min_idx = mid_idx + 1
                else:
                    max_idx = mid_idx
            ret_iter.setitem(ret_state, ret.get_dtype().box(min_idx))
            ret_state = ret_iter.next(ret_state)
            key_state = key_iter.next(key_state)
    return binsearch

binsearch_left = _new_binsearch('left', 'lt')
binsearch_right = _new_binsearch('right', 'le')
