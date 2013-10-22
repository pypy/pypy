from pypy.interpreter.error import OperationError

MODE_CLIP, MODE_WRAP, MODE_RAISE = range(3)

def clipmode_converter(space, w_mode):
    if space.is_none(w_mode):
        return MODE_RAISE
    if space.isinstance_w(w_mode, space.w_str):
        mode = space.str_w(w_mode)
        if mode.startswith('C') or mode.startswith('c'):
            return MODE_CLIP
        if mode.startswith('W') or mode.startswith('w'):
            return MODE_WRAP
        if mode.startswith('R') or mode.startswith('r'):
            return MODE_RAISE
    elif space.isinstance_w(w_mode, space.w_int):
        mode = space.int_w(w_mode)
        if MODE_CLIP <= mode <= MODE_RAISE:
            return mode
    raise OperationError(space.w_TypeError,
                         space.wrap("clipmode not understood"))
