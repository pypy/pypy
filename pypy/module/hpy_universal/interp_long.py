from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles


@API.func("HPy HPyLong_FromLong(HPyContext ctx, long value)")
def HPyLong_FromLong(space, ctx, value):
    w_obj = space.newint(rffi.cast(lltype.Signed, value))
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromLongLong(HPyContext ctx, long long v)")
def HPyLong_FromLongLong(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromUnsignedLongLong(HPyContext ctx, unsigned long long v)")
def HPyLong_FromUnsignedLongLong(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("long HPyLong_AsLong(HPyContext ctx, HPy h)")
def HPyLong_AsLong(space, ctx, h):
    w_obj = handles.deref(space, h)
    #w_obj = space.int(w_obj)     --- XXX write a test for this
    value = space.int_w(w_obj)
    result = rffi.cast(rffi.LONG, value)
    #if rffi.cast(lltype.Signed, result) != value: --- XXX on Windows 64
    #    ...
    return result
