from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib import rutf8
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles

@API.func("int HPyBytes_Check(HPyContext ctx, HPy h)")
def HPyBytes_Check(space, ctx, h):
    w_obj = handles.deref(space, h)
    w_obj_type = space.type(w_obj)
    res = (space.is_w(w_obj_type, space.w_bytes) or
           space.issubtype_w(w_obj_type, space.w_bytes))
    return API.int(res)

@API.func("HPy_ssize_t HPyBytes_Size(HPyContext ctx, HPy h)")
def HPyBytes_Size(space, ctx, h):
    w_obj = handles.deref(space, h)
    return space.len_w(w_obj)

@API.func("HPy_ssize_t HPyBytes_GET_SIZE(HPyContext ctx, HPy h)")
def HPyBytes_GET_SIZE(space, ctx, h):
    return HPyBytes_Size(space, ctx, h)

@API.func("char *HPyBytes_AsString(HPyContext ctx, HPy h)")
def HPyBytes_AsString(space, ctx, h):
    w_obj = handles.deref(space, h)
    s = space.bytes_w(w_obj)
    llbuf, llstring, flag = rffi.get_nonmovingbuffer_ll_final_null(s)
    cb = handles.FreeNonMovingBuffer(llbuf, llstring, flag)
    handles.attach_release_callback(space, h, cb)
    return llbuf


@API.func("char *HPyBytes_AS_STRING(HPyContext ctx, HPy h)")
def HPyBytes_AS_STRING(space, ctx, h):
    return HPyBytes_AsString(space, ctx, h)
