from pypy.interpreter.error import OperationError

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
        out_shape = out_shape + left_shape[:-1] + \
                    right_shape[0:right_critical_dim] + \
                    right_shape[right_critical_dim + 1:]
    elif len(right_shape) > 0:
        #dot does not reduce for scalars
        out_shape = out_shape + left_shape[:-1]
    if my_critical_dim_size != right_critical_dim_size:
        raise OperationError(space.w_ValueError, space.wrap(
                                        "objects are not aligned"))
    return out_shape, right_critical_dim
