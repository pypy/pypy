from pypy.module.micronumpy import interp_ufuncs
from pypy.module.micronumpy.strides import calculate_dot_strides
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.module.micronumpy.interp_iter import ViewIterator


def match_dot_shapes(space, left, right):
    my_critical_dim_size = left.shape[-1]
    right_critical_dim_size = right.shape[0]
    right_critical_dim = 0
    right_critical_dim_stride = right.strides[0]
    out_shape = []
    if len(right.shape) > 1:
        right_critical_dim = len(right.shape) - 2
        right_critical_dim_size = right.shape[right_critical_dim]
        right_critical_dim_stride = right.strides[right_critical_dim]
        assert right_critical_dim >= 0
        out_shape += left.shape[:-1] + \
                     right.shape[0:right_critical_dim] + \
                     right.shape[right_critical_dim + 1:]
    elif len(right.shape) > 0:
        #dot does not reduce for scalars
        out_shape += left.shape[:-1]
    if my_critical_dim_size != right_critical_dim_size:
        raise OperationError(space.w_ValueError, space.wrap(
                                        "objects are not aligned"))
    return out_shape, right_critical_dim


def multidim_dot(space, left, right, result, dtype, right_critical_dim):
    ''' assumes left, right are concrete arrays
    given left.shape == [3, 5, 7],
          right.shape == [2, 7, 4]
     result.shape == [3, 5, 2, 4]
    broadcast shape should be [3, 5, 2, 7, 4]
    result should skip dims 3 which is results.ndims - 1
    left should skip 2, 4 which is a.ndims-1 + range(right.ndims)
          except where it==(right.ndims-2)
    right should skip 0, 1
    '''
    mul = interp_ufuncs.get(space).multiply.func
    add = interp_ufuncs.get(space).add.func
    broadcast_shape = left.shape[:-1] + right.shape
    left_skip = [len(left.shape) - 1 + i for i in range(len(right.shape))
                                         if i != right_critical_dim]
    right_skip = range(len(left.shape) - 1)
    result_skip = [len(result.shape) - 1]
    shapelen = len(broadcast_shape)
    _r = calculate_dot_strides(result.strides, result.backstrides,
                                  broadcast_shape, result_skip)
    outi = ViewIterator(0, _r[0], _r[1], broadcast_shape)
    _r = calculate_dot_strides(left.strides, left.backstrides,
                                  broadcast_shape, left_skip)
    lefti = ViewIterator(0, _r[0], _r[1], broadcast_shape)
    _r = calculate_dot_strides(right.strides, right.backstrides,
                                  broadcast_shape, right_skip)
    righti = ViewIterator(0, _r[0], _r[1], broadcast_shape)
    while not outi.done():
        v = mul(dtype, left.getitem(lefti.offset),
                       right.getitem(righti.offset))
        value = add(dtype, v, result.getitem(outi.offset))
        result.setitem(outi.offset, value)
        outi = outi.next(shapelen)
        righti = righti.next(shapelen)
        lefti = lefti.next(shapelen)
    assert lefti.done()
    assert righti.done()
    return result
