import errno
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.api import cpython_api, CONST_STRING
from pypy.module.cpyext.pyobject import PyObject
from rpython.rlib import rdtoa
from rpython.rlib import rfloat
from rpython.rlib import rposix, jit
from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem import rffi


# PyOS_double_to_string's "type", if non-NULL, will be set to one of:
Py_DTST_FINITE = 0
Py_DTST_INFINITE = 1
Py_DTST_NAN = 2

# Match the "type" back to values in CPython
DOUBLE_TO_STRING_TYPES_MAP = {
    rfloat.DIST_FINITE: Py_DTST_FINITE,
    rfloat.DIST_INFINITY: Py_DTST_INFINITE,
    rfloat.DIST_NAN: Py_DTST_NAN
}

@cpython_api([CONST_STRING, rffi.CCHARPP, PyObject], rffi.DOUBLE, error=-1.0)
@jit.dont_look_inside       # direct use of _get_errno()
def PyOS_string_to_double(space, s, endptr, w_overflow_exception):
    """Convert a string s to a double, raising a Python
    exception on failure.  The set of accepted strings corresponds to
    the set of strings accepted by Python's float() constructor,
    except that s must not have leading or trailing whitespace.
    The conversion is independent of the current locale.

    If endptr is NULL, convert the whole string.  Raise
    ValueError and return -1.0 if the string is not a valid
    representation of a floating-point number.

    If endptr is not NULL, convert as much of the string as
    possible and set *endptr to point to the first unconverted
    character.  If no initial segment of the string is the valid
    representation of a floating-point number, set *endptr to point
    to the beginning of the string, raise ValueError, and return
    -1.0.

    If s represents a value that is too large to store in a float
    (for example, "1e500" is such a string on many platforms) then
    if overflow_exception is NULL return Py_HUGE_VAL (with
    an appropriate sign) and don't set any exception.  Otherwise,
    overflow_exception must point to a Python exception object;
    raise that exception and return -1.0.  In both cases, set
    *endptr to point to the first character after the converted value.

    If any other error occurs during the conversion (for example an
    out-of-memory error), set the appropriate Python exception and
    return -1.0.
    """
    user_endptr = True
    try:
        if not endptr:
            endptr = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
            user_endptr = False
        result = rdtoa.dg_strtod(s, endptr)
        endpos = (rffi.cast(rffi.LONG, endptr[0]) -
                  rffi.cast(rffi.LONG, s))
        if endpos == 0 or (not user_endptr and not endptr[0][0] == '\0'):
            raise oefmt(space.w_ValueError,
                        "invalid input at position %d", endpos)
        err = rffi.cast(lltype.Signed, rposix._get_errno())
        if err == errno.ERANGE:
            rposix._set_errno(rffi.cast(rffi.INT, 0))
            if w_overflow_exception is None:
                if result > 0:
                    return rfloat.INFINITY
                else:
                    return -rfloat.INFINITY
            else:
                raise oefmt(w_overflow_exception, "value too large")
        return result
    finally:
        if not user_endptr:
            lltype.free(endptr, flavor='raw')

@cpython_api([rffi.DOUBLE, lltype.Char, rffi.INT_real, rffi.INT_real, rffi.INTP], rffi.CCHARP)
def PyOS_double_to_string(space, val, format_code, precision, flags, ptype):
    """Convert a double val to a string using supplied
    format_code, precision, and flags.

    format_code must be one of 'e', 'E', 'f', 'F',
    'g', 'G' or 'r'.  For 'r', the supplied precision
    must be 0 and is ignored.  The 'r' format code specifies the
    standard repr() format.

    flags can be zero or more of the values Py_DTSF_SIGN,
    Py_DTSF_ADD_DOT_0, or Py_DTSF_ALT, or-ed together:

    Py_DTSF_SIGN means to always precede the returned string with a sign
    character, even if val is non-negative.

    Py_DTSF_ADD_DOT_0 means to ensure that the returned string will not look
    like an integer.

    Py_DTSF_ALT means to apply "alternate" formatting rules.  See the
    documentation for the PyOS_snprintf() '#' specifier for
    details.

    If ptype is non-NULL, then the value it points to will be set to one of
    Py_DTST_FINITE, Py_DTST_INFINITE, or Py_DTST_NAN, signifying that
    val is a finite number, an infinite number, or not a number, respectively.

    The return value is a pointer to buffer with the converted string or
    NULL if the conversion failed. The caller is responsible for freeing the
    returned string by calling PyMem_Free().
    """
    buffer, rtype = rfloat.double_to_string(val, format_code,
                                            intmask(precision),
                                            intmask(flags))
    if ptype != lltype.nullptr(rffi.INTP.TO):
        ptype[0] = rffi.cast(rffi.INT, DOUBLE_TO_STRING_TYPES_MAP[rtype])
    bufp = rffi.str2charp(buffer)
    return bufp
