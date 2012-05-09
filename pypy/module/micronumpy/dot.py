from pypy.module.micronumpy.strides import calculate_dot_strides
from pypy.interpreter.error import OperationError
from pypy.module.micronumpy.interp_iter import ViewIterator
from pypy.rlib import jit

def dot_printable_location(shapelen):
    return 'numpy dot [%d]' % shapelen

dot_driver = jit.JitDriver(
    greens=['shapelen'],
    reds=['lefti', 'righti', 'outi', 'result', 'right', 'dtype',
          'left'],
    get_printable_location=dot_printable_location,
    name='dot',
)

def match_dot_shapes(space, left, right):
    my_critical_dim_size = left.shape[-1]
    right_critical_dim_size = right.shape[0]
    right_critical_dim = 0
    out_shape = []
    if len(right.shape) > 1:
        right_critical_dim = len(right.shape) - 2
        right_critical_dim_size = right.shape[right_critical_dim]
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
    broadcast_shape = left.shape[:-1] + right.shape
    shapelen = len(broadcast_shape)
    left_skip = [len(left.shape) - 1 + i for i in range(len(right.shape))
                                         if i != right_critical_dim]
    right_skip = range(len(left.shape) - 1)
    result_skip = [len(result.shape) - (len(right.shape) > 1)]
    _r = calculate_dot_strides(result.strides, result.backstrides,
                                  broadcast_shape, result_skip)
    outi = ViewIterator(result.start, _r[0], _r[1], broadcast_shape)
    _r = calculate_dot_strides(left.strides, left.backstrides,
                                  broadcast_shape, left_skip)
    lefti = ViewIterator(left.start, _r[0], _r[1], broadcast_shape)
    _r = calculate_dot_strides(right.strides, right.backstrides,
                                  broadcast_shape, right_skip)
    righti = ViewIterator(right.start, _r[0], _r[1], broadcast_shape)
    while not outi.done():
        dot_driver.jit_merge_point(left=left,
                                   right=right,
                                   shapelen=shapelen,
                                   lefti=lefti,
                                   righti=righti,
                                   outi=outi,
                                   result=result,
                                   dtype=dtype,
                                  )
        lval = left.getitem(lefti.offset).convert_to(dtype) 
        rval = right.getitem(righti.offset).convert_to(dtype) 
        outval = result.getitem(outi.offset).convert_to(dtype) 
        v = dtype.itemtype.mul(lval, rval)
        value = dtype.itemtype.add(v, outval).convert_to(dtype)
        result.setitem(outi.offset, value)
        outi = outi.next(shapelen)
        righti = righti.next(shapelen)
        lefti = lefti.next(shapelen)
    return result
