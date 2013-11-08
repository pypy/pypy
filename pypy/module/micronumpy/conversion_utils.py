from pypy.interpreter.error import OperationError
from pypy.module.micronumpy.constants import *


def byteorder_converter(space, new_order):
    endian = new_order[0]
    if endian not in (NPY_BIG, NPY_LITTLE, NPY_NATIVE, NPY_IGNORE, NPY_SWAP):
        ch = endian
        if ch in ('b', 'B'):
            endian = NPY_BIG
        elif ch in ('l', 'L'):
            endian = NPY_LITTLE
        elif ch in ('n', 'N'):
            endian = NPY_NATIVE
        elif ch in ('i', 'I'):
            endian = NPY_IGNORE
        elif ch in ('s', 'S'):
            endian = NPY_SWAP
        else:
            raise OperationError(space.w_ValueError, space.wrap(
                "%s is an unrecognized byteorder" % new_order))
    return endian


def clipmode_converter(space, w_mode):
    if space.is_none(w_mode):
        return NPY_RAISE
    if space.isinstance_w(w_mode, space.w_str):
        mode = space.str_w(w_mode)
        if mode.startswith('C') or mode.startswith('c'):
            return NPY_CLIP
        if mode.startswith('W') or mode.startswith('w'):
            return NPY_WRAP
        if mode.startswith('R') or mode.startswith('r'):
            return NPY_RAISE
    elif space.isinstance_w(w_mode, space.w_int):
        mode = space.int_w(w_mode)
        if NPY_CLIP <= mode <= NPY_RAISE:
            return mode
    raise OperationError(space.w_TypeError,
                         space.wrap("clipmode not understood"))


def order_converter(space, w_order, default):
    if space.is_none(w_order):
        return default
    if not space.isinstance_w(w_order, space.w_str):
        if space.is_true(w_order):
            return NPY_FORTRANORDER
        else:
            return NPY_CORDER
    else:
        order = space.str_w(w_order)
        if order.startswith('C') or order.startswith('c'):
            return NPY_CORDER
        elif order.startswith('F') or order.startswith('f'):
            return NPY_FORTRANORDER
        elif order.startswith('A') or order.startswith('a'):
            return NPY_ANYORDER
        elif order.startswith('K') or order.startswith('k'):
            return NPY_KEEPORDER
        else:
            raise OperationError(space.w_TypeError, space.wrap(
                "order not understood"))
