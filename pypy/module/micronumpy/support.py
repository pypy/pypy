from rpython.rlib import jit
from pypy.interpreter.error import OperationError

def issequence_w(space, w_obj):
    from pypy.module.micronumpy.base import W_NDimArray
    return (space.isinstance_w(w_obj, space.w_tuple) or
            space.isinstance_w(w_obj, space.w_list) or
            isinstance(w_obj, W_NDimArray))

def index_w(space, w_obj):
    try:
        return space.int_w(space.index(w_obj))
    except OperationError:
        try:
            return space.int_w(space.int(w_obj))
        except OperationError:
            raise OperationError(space.w_IndexError, space.wrap(
                "cannot convert index to integer"))

@jit.unroll_safe
def product(s):
    i = 1
    for x in s:
        i *= x
    return i

@jit.unroll_safe
def calc_strides(shape, dtype, order):
    strides = []
    backstrides = []
    s = 1
    shape_rev = shape[:]
    if order == 'C':
        shape_rev.reverse()
    for sh in shape_rev:
        slimit = max(sh, 1)
        strides.append(s * dtype.elsize)
        backstrides.append(s * (slimit - 1) * dtype.elsize)
        s *= slimit
    if order == 'C':
        strides.reverse()
        backstrides.reverse()
    return strides, backstrides
