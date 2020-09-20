from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError, oefmt
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles
from pypy.module._hpy_universal import llapi

@API.func("HPy HPyDict_New(HPyContext ctx)")
def HPyDict_New(space, ctx):
    w_dict = space.newdict()
    return handles.new(space, w_dict)

@API.func("int HPyDict_Check(HPyContext ctx, HPy h)")
def HPyDict_Check(space, ctx, h):
    w_obj = handles.deref(space, h)
    w_obj_type = space.type(w_obj)
    res = (space.is_w(w_obj_type, space.w_dict) or
           space.issubtype_w(w_obj_type, space.w_dict))
    return API.int(res)

@API.func("int HPyDict_SetItem(HPyContext ctx, HPy h_dict, HPy h_key, HPy h_val)")
def HPyDict_SetItem(space, ctx, h_dict, h_key, h_val):
    w_dict = handles.deref(space, h_dict)
    # XXX the tests should check what happens in this case
    assert isinstance(w_dict, W_DictMultiObject)
    w_key = handles.deref(space, h_key)
    w_val = handles.deref(space, h_val)
    w_dict.setitem(w_key, w_val)
    return API.int(0)

@API.func("HPy HPyDict_GetItem(HPyContext ctx, HPy h_dict, HPy h_key)")
def HPyDict_GetItem(space, ctx, h_dict, h_key):
    w_dict = handles.deref(space, h_dict)
    w_key = handles.deref(space, h_key)
    # XXX the tests should check what happens in this case
    assert isinstance(w_dict, W_DictMultiObject)
    w_result = w_dict.getitem(w_key)
    if w_result is not None:
        return handles.new(space, w_result)
    return llapi.HPy_NULL
