from pypy.interpreter.error import OperationError
from pypy.module.micronumpy import constants as NPY


def byteorder_converter(space, new_order):
    endian = new_order[0]
    if endian not in (NPY.BIG, NPY.LITTLE, NPY.NATIVE, NPY.IGNORE, NPY.SWAP):
        ch = endian
        if ch in ('b', 'B'):
            endian = NPY.BIG
        elif ch in ('l', 'L'):
            endian = NPY.LITTLE
        elif ch in ('n', 'N'):
            endian = NPY.NATIVE
        elif ch in ('i', 'I'):
            endian = NPY.IGNORE
        elif ch in ('s', 'S'):
            endian = NPY.SWAP
        else:
            raise OperationError(space.w_ValueError, space.wrap(
                "%s is an unrecognized byteorder" % new_order))
    return endian


def clipmode_converter(space, w_mode):
    if space.is_none(w_mode):
        return NPY.RAISE
    if space.isinstance_w(w_mode, space.w_str):
        mode = space.str_w(w_mode)
        if mode.startswith('C') or mode.startswith('c'):
            return NPY.CLIP
        if mode.startswith('W') or mode.startswith('w'):
            return NPY.WRAP
        if mode.startswith('R') or mode.startswith('r'):
            return NPY.RAISE
    elif space.isinstance_w(w_mode, space.w_int):
        mode = space.int_w(w_mode)
        if NPY.CLIP <= mode <= NPY.RAISE:
            return mode
    raise OperationError(space.w_TypeError,
                         space.wrap("clipmode not understood"))


def order_converter(space, w_order, default):
    if space.is_none(w_order):
        return default
    if not space.isinstance_w(w_order, space.w_str):
        if space.is_true(w_order):
            return NPY.FORTRANORDER
        else:
            return NPY.CORDER
    else:
        order = space.str_w(w_order)
        if order.startswith('C') or order.startswith('c'):
            return NPY.CORDER
        elif order.startswith('F') or order.startswith('f'):
            return NPY.FORTRANORDER
        elif order.startswith('A') or order.startswith('a'):
            return NPY.ANYORDER
        elif order.startswith('K') or order.startswith('k'):
            return NPY.KEEPORDER
        else:
            raise OperationError(space.w_TypeError, space.wrap(
                "order not understood"))


def multi_axis_converter(space, w_axis, ndim):
    if space.is_none(w_axis):
        return [True] * ndim
    out = [False] * ndim
    if not space.isinstance_w(w_axis, space.w_tuple):
        w_axis = space.newtuple([w_axis])
    for w_item in space.fixedview(w_axis):
        item = space.int_w(w_item)
        axis = item
        if axis < 0:
            axis += ndim
        if axis < 0 or axis >= ndim:
            raise OperationError(space.w_ValueError, space.wrap(
                "'axis' entry %d is out of bounds [-%d, %d)" %
                (item, ndim, ndim)))
        if out[axis]:
            raise OperationError(space.w_ValueError, space.wrap(
                "duplicate value in 'axis'"))
        out[axis] = True
    return out
