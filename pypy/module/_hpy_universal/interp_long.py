from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rarithmetic import maxint
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API


@API.func("HPy HPyLong_FromInt32_t(HPyContext *ctx, int value)")
def HPyLong_FromInt32_t(space, handles, ctx, value):
    # XXX: cpyext does space.newlong: write a test and fix
    w_obj = space.newint(rffi.cast(lltype.Signed, value))
    return handles.new(w_obj)

@API.func("HPy HPyLong_FromUInt32_t(HPyContext *ctx, unsigned int value)")
def HPyLong_FromUInt32_t(space, handles, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(w_obj)

# On windows, long is 4 bytes, on all platforms long long is 8
@API.func("HPy HPyLong_FromInt64_t(HPyContext *ctx, long long v)")
def HPyLong_FromInt64_t(space, handles, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(w_obj)

@API.func("HPy HPyLong_FromUInt64_t(HPyContext *ctx, unsigned long long v)")
def HPyLong_FromUInt64_t(space, handles, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(w_obj)

@API.func("HPy HPyLong_FromSize_t(HPyContext *ctx, size_t value)")
def HPyLong_FromSize_t(space, handles, ctx, v):
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(w_obj)

@API.func("HPy HPyLong_FromSsize_t(HPyContext *ctx, HPy_ssize_t value)")
def HPyLong_FromSsize_t(space, handles, ctx, v):
    # XXX: cpyext uses space.newlong: is there any difference?
    w_obj = space.newlong_from_rarith_int(v)
    return handles.new(w_obj)

ULONG_MASK = (2 ** (8 * rffi.sizeof(rffi.ULONG)) -1)
ULONG_MAX = (2 ** (8 * rffi.sizeof(rffi.ULONG)) -1)
LONG_MAX = (2 ** (8 * rffi.sizeof(rffi.ULONG) - 1) -1)
LONG_MIN = (-2 ** (8 * rffi.sizeof(rffi.ULONG) - 1))
need_to_check = maxint > ULONG_MAX

@API.func("long HPyLong_AsInt32_t(HPyContext *ctx, HPy h)",
          error_value=API.cast("long", -1))
def HPyLong_AsInt32_t(space, handles, ctx, h):
    w_long = handles.deref(h)
    val = space.int_w(space.int(w_long))
    if need_to_check and (val > LONG_MAX or val < LONG_MIN):
        # On win64 space.int_w will succeed for 8-byte ints
        # but long is 4 bytes. So we must check manually
        raise oefmt(space.w_OverflowError,
                    "Python int too large to convert to C long")
    return rffi.cast(rffi.LONG, val)

@API.func("unsigned long HPyLong_AsUInt32_t(HPyContext *ctx, HPy h)",
          error_value=API.cast("unsigned long", -1))
def HPyLong_AsUInt32_t(space, handles, ctx, h):
    w_long = handles.deref(h)
    try:
        val = space.uint_w(w_long)
    except OperationError as e:
        if e.match(space, space.w_ValueError):
            e.w_type = space.w_OverflowError
        raise
    if need_to_check and val > ULONG_MAX:
        # On win64 space.uint_w will succeed for 8-byte ints
        # but long is 4 bytes. So we must check manually
        raise oefmt(space.w_OverflowError,
                    "Python int too large to convert to C unsigned long")
    return rffi.cast(rffi.ULONG, val)

@API.func("unsigned long HPyLong_AsUInt32_tMask(HPyContext *ctx, HPy h)",
          error_value=API.cast("unsigned long", -1))
def HPyLong_AsUInt32_tMask(space, handles, ctx, h):
    w_long = handles.deref(h)
    num = space.bigint_w(w_long)
    val = num.uintmask()
    if need_to_check and not we_are_translated():
        # On win64 num.uintmask will succeed for 8-byte ints
        # but unsigned long is 4 bytes.
        # The cast below is sufficient when translated, but
        # we need an extra check when running on CPython.
        val &= ULONG_MASK
    return rffi.cast(rffi.ULONG, val)

@API.func("long long HPyLong_AsInt64_t(HPyContext *ctx, HPy h)",
          error_value=API.cast("long long", -1))
def HPyLong_AsInt64_t(space, handles, ctx, h):
    w_long = handles.deref(h)
    return rffi.cast(rffi.LONGLONG, space.r_longlong_w(w_long))

@API.func("unsigned long long HPyLong_AsUInt64_t(HPyContext *ctx, HPy h)",
          error_value=API.cast("unsigned long long", -1))
def HPyLong_AsUInt64_t(space, handles, ctx, h):
    w_long = handles.deref(h)
    try:
        return rffi.cast(rffi.ULONGLONG, space.r_ulonglong_w(
            w_long, allow_conversion=False))
    except OperationError as e:
        if e.match(space, space.w_ValueError):
            e.w_type = space.w_OverflowError
        raise

@API.func("unsigned long long HPyLong_AsUInt64_tMask(HPyContext *ctx, HPy h)",
          error_value=API.cast("unsigned long long", -1))
def HPyLong_AsUInt64_tMask(space, handles, ctx, h):
    w_long = handles.deref(h)
    num = space.bigint_w(w_long)
    return num.ulonglongmask()

@API.func("size_t HPyLong_AsSize_t(HPyContext *ctx, HPy h)",
          error_value=API.cast("size_t", -1))
def HPyLong_AsSize_t(space, handles, ctx, h):
    w_long = handles.deref(h)
    try:
        return space.uint_w(w_long)
    except OperationError as e:
        if e.match(space, space.w_ValueError):
            e.w_type = space.w_OverflowError
        raise

@API.func("HPy_ssize_t HPyLong_AsSsize_t(HPyContext *ctx, HPy h)",
          error_value=API.cast("ssize_t", -1))
def HPyLong_AsSsize_t(space, handles, ctx, h):
    w_long = handles.deref(h)
    return space.int_w(w_long, allow_conversion=False)

@API.func("void * HPyLong_AsVoidPtr(HPyContext *ctx, HPy h)")
def HPyLong_AsVoidPtr(space, handles, ctx, h):
    w_long = handles.deref(h)
    return rffi.cast(rffi.VOIDP, space.int_w(w_long, allow_conversion=False))

@API.func("double HPyLong_AsDouble(HPyContext *ctx, HPy h)",
          error_value=-1.0)
def HPyLong_AsDouble(space, handles, ctx, h):
    w_long = handles.deref(h)
    return space.float_w(w_long)
