from pypy.interpreter.error import OperationError
from pypy.module.micronumpy.constants import *

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
