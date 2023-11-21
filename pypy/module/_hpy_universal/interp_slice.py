import sys
from pypy.interpreter.error import oefmt
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.module._hpy_universal.apiset import API

@API.func("int HPySlice_Unpack(HPyContext *ctx, HPy h, HPy_ssize_t *start, HPy_ssize_t *stop, HPy_ssize_t *step)", error_value=API.int(-1))
def HPySlice_Unpack(space, handles, ctx, h, start_p, stop_p, step_p):
    if not h:
        raise oefmt(space.w_SystemError, "NULL handle passed to HPySlice_Unpack")
    w_slice = handles.deref(h)
    if not isinstance(w_slice, W_SliceObject):
        raise oefmt(space.w_SystemError, "non-slice passed to HPySlice_Unpack")

    if space.is_none(w_slice.w_step):
        step = 1
    else:
        step = W_SliceObject.eval_slice_index(space, w_slice.w_step)
        if step == 0:
            raise oefmt(space.w_ValueError, "slice step cannot be zero")
        if step < -sys.maxint:
            step = -sys.maxint
    step_p[0] = step

    if space.is_none(w_slice.w_start):
        start = sys.maxint if step < 0 else 0
    else:
        start = W_SliceObject.eval_slice_index(space, w_slice.w_start)
    start_p[0] = start

    if space.is_none(w_slice.w_stop):
        stop = -sys.maxint-1 if step < 0 else sys.maxint
    else:
        stop = W_SliceObject.eval_slice_index(space, w_slice.w_stop)
    stop_p[0] = stop

    return API.int(0)

