
from numarray import NumArray
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError

def minimum(space, w_a, w_b):
    if not isinstance(w_a, NumArray) or not isinstance(w_b, NumArray):
        raise OperationError(space.w_TypeError,
                             space.wrap("expecting NumArrat object"))
    if w_a.dim != w_b.dim:
        raise OperationError(space.w_ValueError,
                             space.wrap("minimum of arrays of different length"))
    res = NumArray(space, w_a.dim, 'i')
    for i in range(len(w_a.storage)):
        one = w_a.storage[i]
        two = w_b.storage[i]
        if one < two:
            res.storage[i] = one
        else:
            res.storage[i] = two
    return space.wrap(res)
minimum.unwrap_spec = [ObjSpace, W_Root, W_Root]
