from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles

@API.func("HPy HPyFloat_FromDouble(HPyContext ctx, double v)")
def HPyFloat_FromDouble(space, ctx, v):
    w_obj = space.newfloat(v)
    return handles.new(space, w_obj)

@API.func("double HPyFloat_AsDouble(HPyContext ctx, HPy h)")
def HPyFloat_AsDouble(space, ctx, h):
    # XXX: the cpyext version calls space.float_w(space.float(w_obj)): we need
    # to add a test in HPy to test for that, and fix
    w_obj = handles.deref(space, h)
    value = space.float_w(w_obj)
    return value
