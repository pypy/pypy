from pypy.module.micronumpy.strides import calculate_dot_strides
from pypy.interpreter.error import OperationError
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
    left_shape = left.get_shape()
    right_shape = right.get_shape()
    my_critical_dim_size = left_shape[-1]
    right_critical_dim_size = right_shape[0]
    right_critical_dim = 0
    out_shape = []
    if len(right_shape) > 1:
        right_critical_dim = len(right_shape) - 2
        right_critical_dim_size = right_shape[right_critical_dim]
        assert right_critical_dim >= 0
        out_shape += left_shape[:-1] + \
                     right_shape[0:right_critical_dim] + \
                     right_shape[right_critical_dim + 1:]
    elif len(right_shape) > 0:
        #dot does not reduce for scalars
        out_shape += left_shape[:-1]
    if my_critical_dim_size != right_critical_dim_size:
        raise OperationError(space.w_ValueError, space.wrap(
                                        "objects are not aligned"))
    return out_shape, right_critical_dim
