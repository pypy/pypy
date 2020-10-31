from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
import pypy.module.__builtin__.operation as operation
from pypy.objspace.std.bytesobject import invoke_bytes_method
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles
from . import llapi

@API.func("int HPy_IsTrue(HPyContext ctx, HPy h)")
def HPy_IsTrue(space, ctx, h_obj):
    w_obj = handles.deref(space, h_obj)
    return API.int(space.is_true(w_obj))

@API.func("HPy HPy_GetAttr(HPyContext ctx, HPy obj, HPy h_name)")
def HPy_GetAttr(space, ctx, h_obj, h_name):
    w_obj = handles.deref(space, h_obj)
    w_name = handles.deref(space, h_name)
    w_res = space.getattr(w_obj, w_name)
    return handles.new(space, w_res)

@API.func("HPy HPy_GetAttr_s(HPyContext ctx, HPy h_obj, const char *name)")
def HPy_GetAttr_s(space, ctx, h_obj, name):
    w_obj = handles.deref(space, h_obj)
    w_name = API.ccharp2text(space, name)
    w_res = space.getattr(w_obj, w_name)
    return handles.new(space, w_res)


@API.func("int HPy_HasAttr(HPyContext ctx, HPy h_obj, HPy h_name)")
def HPy_HasAttr(space, ctx, h_obj, h_name):
    w_obj = handles.deref(space, h_obj)
    w_name = handles.deref(space, h_name)
    return _HasAttr(space, w_obj, w_name)

@API.func("int HPy_HasAttr_s(HPyContext ctx, HPy h_obj, const char *name)")
def HPy_HasAttr_s(space, ctx, h_obj, name):
    w_obj = handles.deref(space, h_obj)
    w_name = API.ccharp2text(space, name)
    return _HasAttr(space, w_obj, w_name)

def _HasAttr(space, w_obj, w_name):
    try:
        w_res = operation.hasattr(space, w_obj, w_name)
        return API.int(space.is_true(w_res))
    except OperationError:
        return API.int(0)


@API.func("int HPy_SetAttr(HPyContext ctx, HPy h_obj, HPy h_name, HPy h_value)")
def HPy_SetAttr(space, ctx, h_obj, h_name, h_value):
    w_obj = handles.deref(space, h_obj)
    w_name = handles.deref(space, h_name)
    w_value = handles.deref(space, h_value)
    operation.setattr(space, w_obj, w_name, w_value)
    return API.int(0)

@API.func("int HPy_SetAttr_s(HPyContext ctx, HPy h_obj, const char *name, HPy h_value)")
def HPy_SetAttr_s(space, ctx, h_obj, name, h_value):
    w_obj = handles.deref(space, h_obj)
    w_name = API.ccharp2text(space, name)
    w_value = handles.deref(space, h_value)
    operation.setattr(space, w_obj, w_name, w_value)
    return API.int(0)


@API.func("HPy HPy_GetItem(HPyContext ctx, HPy h_obj, HPy h_key)")
def HPy_GetItem(space, ctx, h_obj, h_key):
    w_obj = handles.deref(space, h_obj)
    w_key = handles.deref(space, h_key)
    w_res = space.getitem(w_obj, w_key)
    return handles.new(space, w_res)

@API.func("HPy HPy_GetItem_i(HPyContext ctx, HPy h_obj, HPy_ssize_t idx)")
def HPy_GetItem_i(space, ctx, h_obj, idx):
    w_obj = handles.deref(space, h_obj)
    w_key = space.newint(idx)
    w_res = space.getitem(w_obj, w_key)
    return handles.new(space, w_res)

@API.func("HPy HPy_GetItem_s(HPyContext ctx, HPy h_obj, const char *key)")
def HPy_GetItem_s(space, ctx, h_obj, key):
    w_obj = handles.deref(space, h_obj)
    w_key = API.ccharp2text(space, key)
    w_res = space.getitem(w_obj, w_key)
    return handles.new(space, w_res)


@API.func("int HPy_SetItem(HPyContext ctx, HPy h_obj, HPy h_key, HPy h_val)")
def HPy_SetItem(space, ctx, h_obj, h_key, h_val):
    w_obj = handles.deref(space, h_obj)
    w_key = handles.deref(space, h_key)
    w_val = handles.deref(space, h_val)
    space.setitem(w_obj, w_key, w_val)
    return API.int(0)

@API.func("int HPy_SetItem_i(HPyContext ctx, HPy h_obj, HPy_ssize_t idx, HPy h_val)")
def HPy_SetItem_i(space, ctx, h_obj, idx, h_val):
    w_obj = handles.deref(space, h_obj)
    w_key = space.newint(idx)
    w_val = handles.deref(space, h_val)
    space.setitem(w_obj, w_key, w_val)
    return API.int(0)

@API.func("int HPy_SetItem_s(HPyContext ctx, HPy h_obj, const char *key, HPy h_val)")
def HPy_SetItem_s(space, ctx, h_obj, key, h_val):
    w_obj = handles.deref(space, h_obj)
    w_key = API.ccharp2text(space, key)
    w_val = handles.deref(space, h_val)
    space.setitem(w_obj, w_key, w_val)
    return API.int(0)

@API.func("HPy HPy_Repr(HPyContext ctx, HPy h_obj)")
def HPy_Repr(space, ctx, h_obj):
    # XXX: cpyext checks and returns <NULL>. Add a test to HPy and fix here
    w_obj = handles.deref(space, h_obj)
    w_res = space.repr(w_obj)
    return handles.new(space, w_res)

@API.func("HPy HPy_Str(HPyContext ctx, HPy h_obj)")
def HPy_Str(space, ctx, h_obj):
    # XXX: cpyext checks and returns <NULL>. Add a test to HPy and fix here
    w_obj = handles.deref(space, h_obj)
    w_res = space.str(w_obj)
    return handles.new(space, w_res)

@API.func("HPy HPy_ASCII(HPyContext ctx, HPy h_obj)")
def HPy_ASCII(space, ctx, h_obj):
    w_obj = handles.deref(space, h_obj)
    w_res = operation.ascii(space, w_obj)
    return handles.new(space, w_res)

@API.func("HPy HPy_Bytes(HPyContext ctx, HPy h_obj)")
def HPy_Bytes(space, ctx, h_obj):
    # XXX: cpyext checks and returns <NULL>. Add a test to HPy and fix here
    w_obj = handles.deref(space, h_obj)
    if space.type(w_obj) is space.w_bytes:
        # XXX write a test for this case
        return handles.dup(space, h_obj)
    w_result = invoke_bytes_method(space, w_obj)
    if w_result is not None:
        return handles.new(space, w_result)
    # return PyBytes_FromObject(space, w_obj)
    # XXX: write a test for this case
    buffer = space.buffer_w(w_obj, space.BUF_FULL_RO)
    w_res = space.newbytes(buffer.as_str())
    return handles.new(space, w_res)

@API.func("HPy HPy_RichCompare(HPyContext ctx, HPy v, HPy w, int op)")
def HPy_RichCompare(space, ctx, v, w, op):
    w_o1 = handles.deref(space, v)
    w_o2 = handles.deref(space, w)
    w_result = rich_compare(space, w_o1, w_o2, op)
    return handles.new(space, w_result)

def rich_compare(space, w_o1, w_o2, opid_int):
    opid = rffi.cast(lltype.Signed, opid_int)
    if opid == llapi.HPy_LT:
        return space.lt(w_o1, w_o2)
    elif opid == llapi.HPy_LE:
        return space.le(w_o1, w_o2)
    elif opid == llapi.HPy_EQ:
        return space.eq(w_o1, w_o2)
    elif opid == llapi.HPy_NE:
        return space.ne(w_o1, w_o2)
    elif opid == llapi.HPy_GT:
        return space.gt(w_o1, w_o2)
    elif opid == llapi.HPy_GE:
        return space.ge(w_o1, w_o2)
    else:
        raise oefmt(space.w_SystemError, "Bad internal call!")


@API.func("int HPy_RichCompareBool(HPyContext ctx, HPy v, HPy w, int op)")
def HPy_RichCompareBool(space, ctx, v, w, op):
    w_o1 = handles.deref(space, v)
    w_o2 = handles.deref(space, w)
    # Quick result when objects are the same.
    # Guarantees that identity implies equality.
    if space.is_w(w_o1, w_o2):
        opid = rffi.cast(lltype.Signed, op)
        if opid == llapi.HPy_EQ:
            return API.int(1)
        if opid == llapi.HPy_NE:
            return API.int(0)
    w_result = rich_compare(space, w_o1, w_o2, op)
    return API.int(space.is_true(w_result))

@API.func("HPy_hash_t HPy_Hash(HPyContext ctx, HPy obj)")
def HPy_Hash(space, ctx, h_obj):
    w_obj = handles.deref(space, h_obj)
    return API.cts.cast('HPy_hash_t', space.hash_w(w_obj))

@API.func("HPy_ssize_t HPy_Length(HPyContext ctx, HPy h)")
def HPy_Length(space, ctx, h_obj):
    w_obj = handles.deref(space, h_obj)
    return space.len_w(w_obj)
