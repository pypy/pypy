from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles


@API.func("HPy HPyLong_FromLong(HPyContext ctx, long value)")
def HPyLong_FromLong(space, ctx, value):
    # XXX: cpyext does space.newlong: write a test and fix
    w_obj = space.newint(rffi.cast(lltype.Signed, value))
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromUnsignedLong(HPyContext ctx, unsigned long value)")
def HPyLong_FromUnsignedLong(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromLongLong(HPyContext ctx, long long v)")
def HPyLong_FromLongLong(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromUnsignedLongLong(HPyContext ctx, unsigned long long v)")
def HPyLong_FromUnsignedLongLong(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromSize_t(HPyContext ctx, size_t value)")
def HPyLong_FromSize_t(space, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("HPy HPyLong_FromSsize_t(HPyContext ctx, HPy_ssize_t value)")
def HPyLong_FromSsize_t(space, ctx, v):
    # XXX: cpyext uses space.newlong: is there any difference?
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(space, w_obj)

@API.func("long HPyLong_AsLong(HPyContext ctx, HPy h)",
          error_value=API.cast("long", -1))
def HPyLong_AsLong(space, ctx, h):
    w_long = handles.deref(space, h)
    return space.int_w(space.int(w_long))

@API.func("unsigned long HPyLong_AsUnsignedLong(HPyContext ctx, HPy h)",
          error_value=API.cast("unsigned long", -1))
def HPyLong_AsUnsignedLong(space, ctx, h):
    w_long = handles.deref(space, h)
    try:
        return rffi.cast(rffi.ULONG, space.uint_w(w_long))
    except OperationError as e:
        if e.match(space, space.w_ValueError):
            e.w_type = space.w_OverflowError
        raise

@API.func("unsigned long HPyLong_AsUnsignedLongMask(HPyContext ctx, HPy h)",
          error_value=API.cast("unsigned long", -1))
def HPyLong_AsUnsignedLongMask(space, ctx, h):
    w_long = handles.deref(space, h)
    num = space.bigint_w(w_long)
    return num.uintmask()

@API.func("long long HPyLong_AsLongLong(HPyContext ctx, HPy h)",
          error_value=API.cast("long long", -1))
def HPyLong_AsLongLong(space, ctx, h):
    w_long = handles.deref(space, h)
    return rffi.cast(rffi.LONGLONG, space.r_longlong_w(w_long))

@API.func("unsigned long long HPyLong_AsUnsignedLongLong(HPyContext ctx, HPy h)",
          error_value=API.cast("unsigned long long", -1))
def HPyLong_AsUnsignedLongLong(space, ctx, h):
    w_long = handles.deref(space, h)
    try:
        return rffi.cast(rffi.ULONGLONG, space.r_ulonglong_w(w_long))
    except OperationError as e:
        if e.match(space, space.w_ValueError):
            e.w_type = space.w_OverflowError
        raise

@API.func("unsigned long long HPyLong_AsUnsignedLongLongMask(HPyContext ctx, HPy h)",
          error_value=API.cast("unsigned long long", -1))
def HPyLong_AsUnsignedLongLongMask(space, ctx, h):
    w_long = handles.deref(space, h)
    num = space.bigint_w(w_long)
    return num.ulonglongmask()

@API.func("size_t HPyLong_AsSize_t(HPyContext ctx, HPy h)",
          error_value=API.cast("size_t", -1))
def HPyLong_AsSize_t(space, ctx, h):
    w_long = handles.deref(space, h)
    try:
        return space.uint_w(w_long)
    except OperationError as e:
        if e.match(space, space.w_ValueError):
            e.w_type = space.w_OverflowError
        raise

@API.func("HPy_ssize_t HPyLong_AsSsize_t(HPyContext ctx, HPy h)",
          error_value=API.cast("ssize_t", -1))
def HPyLong_AsSsize_t(space, ctx, h):
    w_long = handles.deref(space, h)
    return space.int_w(w_long)
