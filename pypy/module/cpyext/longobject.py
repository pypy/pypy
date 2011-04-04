from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import (cpython_api, PyObject, build_type_checkers,
                                    CONST_STRING, ADDR, CANNOT_FAIL)
from pypy.objspace.std.longobject import W_LongObject
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.intobject import PyInt_AsUnsignedLongMask
from pypy.rlib.rbigint import rbigint
from pypy.rlib.rarithmetic import intmask


PyLong_Check, PyLong_CheckExact = build_type_checkers("Long")

@cpython_api([lltype.Signed], PyObject)
def PyLong_FromLong(space, val):
    """Return a new PyLongObject object from v, or NULL on failure."""
    return space.newlong(val)

@cpython_api([rffi.LONGLONG], PyObject)
def PyLong_FromLongLong(space, val):
    """Return a new PyLongObject object from a C long long, or NULL
    on failure."""
    return space.wrap(val)

@cpython_api([rffi.ULONG], PyObject)
def PyLong_FromUnsignedLong(space, val):
    """Return a new PyLongObject object from a C unsigned long, or
    NULL on failure."""
    return space.wrap(val)

@cpython_api([rffi.ULONGLONG], PyObject)
def PyLong_FromUnsignedLongLong(space, val):
    """Return a new PyLongObject object from a C unsigned long long,
    or NULL on failure."""
    return space.wrap(val)

@cpython_api([PyObject], rffi.ULONG, error=-1)
def PyLong_AsUnsignedLong(space, w_long):
    """
    Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised."""
    return rffi.cast(rffi.ULONG, space.uint_w(w_long))

@cpython_api([PyObject], rffi.ULONG, error=-1)
def PyLong_AsUnsignedLongMask(space, w_long):
    """Return a C unsigned long from a Python long integer, without checking
    for overflow.
    """
    return PyInt_AsUnsignedLongMask(space, w_long)

@cpython_api([PyObject], lltype.Signed, error=-1)
def PyLong_AsLong(space, w_long):
    """
    Return a C long representation of the contents of pylong.  If
    pylong is greater than LONG_MAX, an OverflowError is raised
    and -1 will be returned."""
    return space.int_w(w_long)

@cpython_api([PyObject], rffi.LONGLONG, error=-1)
def PyLong_AsLongLong(space, w_long):
    """
    Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised."""
    return rffi.cast(rffi.LONGLONG, space.r_longlong_w(w_long))

@cpython_api([PyObject], rffi.ULONGLONG, error=-1)
def PyLong_AsUnsignedLongLong(space, w_long):
    """
    Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised."""
    return rffi.cast(rffi.ULONGLONG, space.r_ulonglong_w(w_long))

@cpython_api([PyObject], rffi.ULONGLONG, error=-1)
def PyLong_AsUnsignedLongLongMask(space, w_long):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    unsigned long long, without checking for overflow.
    """
    num = space.bigint_w(w_long)
    return num.ulonglongmask()

@cpython_api([PyObject, rffi.CArrayPtr(rffi.INT_real)], lltype.Signed,
             error=-1)
def PyLong_AsLongAndOverflow(space, w_long, overflow_ptr):
    """
    Return a C long representation of the contents of pylong.  If pylong is
    greater than LONG_MAX or less than LONG_MIN, set *overflow to 1 or -1,
    respectively, and return -1; otherwise, set *overflow to 0.  If any other
    exception occurs (for example a TypeError or MemoryError), then -1 will be
    returned and *overflow will be 0."""
    overflow_ptr[0] = rffi.cast(rffi.INT_real, 0)
    try:
        return space.int_w(w_long)
    except OperationError, e:
        if not e.match(space, space.w_OverflowError):
            raise
    if space.is_true(space.gt(w_long, space.wrap(0))):
        overflow_ptr[0] = rffi.cast(rffi.INT_real, 1)
    else:
        overflow_ptr[0] = rffi.cast(rffi.INT_real, -1)
    return -1

@cpython_api([PyObject, rffi.CArrayPtr(rffi.INT_real)], rffi.LONGLONG,
             error=-1)
def PyLong_AsLongLongAndOverflow(space, w_long, overflow_ptr):
    """
    Return a C long long representation of the contents of pylong.  If pylong is
    greater than PY_LLONG_MAX or less than PY_LLONG_MIN, set *overflow to 1 or
    -1, respectively, and return -1; otherwise, set *overflow to 0.  If any
    other exception occurs (for example a TypeError or MemoryError), then -1
    will be returned and *overflow will be 0."""
    overflow_ptr[0] = rffi.cast(rffi.INT_real, 0)
    try:
        return rffi.cast(rffi.LONGLONG, space.r_longlong_w(w_long))
    except OperationError, e:
        if not e.match(space, space.w_OverflowError):
            raise
    if space.is_true(space.gt(w_long, space.wrap(0))):
        overflow_ptr[0] = rffi.cast(rffi.INT_real, 1)
    else:
        overflow_ptr[0] = rffi.cast(rffi.INT_real, -1)
    return -1

@cpython_api([lltype.Float], PyObject)
def PyLong_FromDouble(space, val):
    """Return a new PyLongObject object from v, or NULL on failure."""
    return space.long(space.wrap(val))

@cpython_api([PyObject], lltype.Float, error=-1.0)
def PyLong_AsDouble(space, w_long):
    """Return a C double representation of the contents of pylong.  If
    pylong cannot be approximately represented as a double, an
    OverflowError exception is raised and -1.0 will be returned."""
    return space.float_w(space.float(w_long))

@cpython_api([CONST_STRING, rffi.CCHARPP, rffi.INT_real], PyObject)
def PyLong_FromString(space, str, pend, base):
    """Return a new PyLongObject based on the string value in str, which is
    interpreted according to the radix in base.  If pend is non-NULL,
    *pend will point to the first character in str which follows the
    representation of the number.  If base is 0, the radix will be determined
    based on the leading characters of str: if str starts with '0x' or
    '0X', radix 16 will be used; if str starts with '0', radix 8 will be
    used; otherwise radix 10 will be used.  If base is not 0, it must be
    between 2 and 36, inclusive.  Leading spaces are ignored.  If there are
    no digits, ValueError will be raised."""
    s = rffi.charp2str(str)
    w_str = space.wrap(s)
    w_base = space.wrap(rffi.cast(lltype.Signed, base))
    if pend:
        pend[0] = rffi.ptradd(str, len(s))
    return space.call_function(space.w_long, w_str, w_base)

@cpython_api([rffi.VOIDP], PyObject)
def PyLong_FromVoidPtr(space, p):
    """Create a Python integer or long integer from the pointer p. The pointer value
    can be retrieved from the resulting value using PyLong_AsVoidPtr().

    If the integer is larger than LONG_MAX, a positive long integer is returned."""
    return space.wrap(rffi.cast(ADDR, p))

@cpython_api([PyObject], rffi.VOIDP, error=lltype.nullptr(rffi.VOIDP.TO))
def PyLong_AsVoidPtr(space, w_long):
    """Convert a Python integer or long integer pylong to a C void pointer.
    If pylong cannot be converted, an OverflowError will be raised.  This
    is only assured to produce a usable void pointer for values created
    with PyLong_FromVoidPtr().
    For values outside 0..LONG_MAX, both signed and unsigned integers are accepted."""
    return rffi.cast(rffi.VOIDP, space.uint_w(w_long))

@cpython_api([PyObject], rffi.SIZE_T, error=-1)
def _PyLong_NumBits(space, w_long):
    return space.uint_w(space.call_method(w_long, "bit_length"))

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def _PyLong_Sign(space, w_long):
    assert isinstance(w_long, W_LongObject)
    return w_long.num.sign

UCHARP = rffi.CArrayPtr(rffi.UCHAR)
@cpython_api([UCHARP, rffi.SIZE_T, rffi.INT_real, rffi.INT_real], PyObject)
def _PyLong_FromByteArray(space, bytes, n, little_endian, signed):
    little_endian = rffi.cast(lltype.Signed, little_endian)
    signed = rffi.cast(lltype.Signed, signed)

    result = rbigint()
    negative = False

    for i in range(0, n):
        if little_endian:
            c = intmask(bytes[i])
        else:
            c = intmask(bytes[n - i - 1])
        if i == 0 and signed and c & 0x80:
            negative = True
        if negative:
            c = c ^ 0xFF
        digit = rbigint.fromint(c)

        result = result.lshift(8)
        result = result.add(digit)

    if negative:
        result = result.neg()

    return space.newlong_from_rbigint(result)

