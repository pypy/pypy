import sys
from pypy.interpreter.error import oefmt
from pypy.objspace.std.sliceobject import W_SliceObject
from .apiset import API
from pypy.interpreter.error import OperationError, oefmt

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

@API.func("HPy HPySlice_New(HPyContext *ctx, HPy start, HPy stop, HPy step)")
def HPySlice_New(space, handles, ctx, h_start, h_stop, h_step):
    w_start = handles.deref(h_start)
    w_stop = handles.deref(h_stop)
    w_step = handles.deref(h_step)
    return handles.new(W_SliceObject(w_start, w_stop, w_step))

@API.func("int HPyIter_Check(HPyContext *ctx, HPy obj)", error_value=API.int(-1))
def HPyIter_Check(space, handles, ctx, h_obj):
    w_obj = handles.deref(h_obj)
    try:
        w_attr = space.getattr(space.type(w_obj), space.newtext("__next__"))
    except:
        pass
    else:
        if space.is_true(space.callable(w_attr)):
            return API.int(1)
    return API.int(0)

@API.func("HPy HPy_GetIter(HPyContext *ctx, HPy obj)")
def HPy_GetIter(space, handles, ctx, h_obj):
    w_obj = handles.deref(h_obj)
    return handles.new(space.iter(w_obj))

@API.func("HPy HPyIter_Next(HPyContext *ctx, HPy obj)")
def HPyIter_Next(space, handles, ctx, h_obj):
    w_obj = handles.deref(h_obj)
    try:
        ret = space.next(w_obj)
    except OperationError as e:
        if not e.match(space, space.w_StopIteration):
            raise
        return 0
    return handles.new(ret)

@API.func("int HPy_DelSlice(HPyContext *ctx, HPy obj, HPy_ssize_t start, HPy_ssize_t end)", error_value=API.int(-1))
def HPy_DelSlice(space, handles, ctx, h_obj, start, end):
    if not h_obj:
        raise oefmt(space.w_SystemError, "NULL handle passed to HPy_DelSlice")
    w_obj = handles.deref(h_obj)
    space.delslice(w_obj, space.newint(start), space.newint(end))
    return API.int(0)
    
@API.func("int HPy_SetSlice(HPyContext *ctx, HPy obj, HPy_ssize_t start, HPy_ssize_t end, HPy value)", error_value=API.int(-1))
def HPy_SetSlice(space, handles, ctx, h_obj, start, end, h_value):
    if not h_obj:
        raise oefmt(space.w_SystemError, "NULL handle passed to HPy_SetSlice")
    w_obj = handles.deref(h_obj)
    if not h_value:
        space.delslice(w_obj, space.newint(start), space.newint(end))
        return API.int(0)
    w_value = handles.deref(h_value)
    space.setslice(w_obj, space.newint(start), space.newint(end), w_value)
    return API.int(0)

@API.func("HPy HPy_GetSlice(HPyContext *ctx, HPy obj, HPy_ssize_t start, HPy_ssize_t end)")
def HPy_GetSlice(space, handles, ctx, h_obj, start, end):
    if not h_obj:
        raise oefmt(space.w_SystemError, "NULL handle passed to HPy_GetSlice")
    w_obj = handles.deref(h_obj)
    ret = space.getslice(w_obj, space.newint(start), space.newint(end))
    return handles.new(ret)

