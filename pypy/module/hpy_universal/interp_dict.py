from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError, oefmt
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles

@API.func("HPy HPyDict_New(HPyContext ctx)")
def HPyDict_New(space, ctx):
    w_dict = space.newdict()
    return handles.new(space, w_dict)

@API.func("int HPyDict_SetItem(HPyContext ctx, HPy h_dict, HPy h_key, HPy h_val)")
def HPyDict_SetItem(space, ctx, h_dict, h_key, h_val):
    w_dict = handles.deref(space, h_dict)
    # XXX the tests should check what happens in this case
    assert isinstance(w_dict, W_DictMultiObject)
    w_key = handles.deref(space, h_key)
    w_val = handles.deref(space, h_val)
    w_dict.setitem(w_key, w_val)
    return rffi.cast(rffi.INT_real, 0)
