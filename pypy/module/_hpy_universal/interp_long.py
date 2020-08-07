from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles


@API.func("HPy HPyLong_FromLong(HPyContext ctx, long value)")
def HPyLong_FromLong(space, ctx, value):
    w_obj = space.newint(rffi.cast(lltype.Signed, value))
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromUnsignedLong(HPyContext ctx, unsigned long value)")
def HPyLong_FromUnsignedLong(space, ctx, value):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPyLong_FromLongLong(HPyContext ctx, long long v)")
def HPyLong_FromLongLong(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromUnsignedLongLong(HPyContext ctx, unsigned long long v)")
def HPyLong_FromUnsignedLongLong(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromSize_t(HPyContext ctx, size_t value)")
def HPyLong_FromSize_t(space, ctx, value):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("HPy HPyLong_FromSsize_t(HPyContext ctx, HPy_ssize_t value)")
def HPyLong_FromSsize_t(space, ctx, value):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError

@API.func("long HPyLong_AsLong(HPyContext ctx, HPy h)")
def HPyLong_AsLong(space, ctx, h):
    w_obj = handles.deref(space, h)
    #w_obj = space.int(w_obj)     --- XXX write a test for this
    value = space.int_w(w_obj)
    result = rffi.cast(rffi.LONG, value)
    #if rffi.cast(lltype.Signed, result) != value: --- XXX on Windows 64
    #    ...
    return result
