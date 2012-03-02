import errno
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api
from pypy.module.cpyext.pyobject import PyObject
from pypy.rlib import rdtoa
from pypy.rlib import rfloat
from pypy.rlib import rposix
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rffi


@cpython_api([rffi.CCHARP, rffi.CCHARPP, PyObject], rffi.DOUBLE, error=-1.0)
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
            raise OperationError(
                space.w_ValueError,
                space.wrap('invalid input at position %s' % endpos))
        if rposix.get_errno() == errno.ERANGE:
            rposix.set_errno(0)
            if w_overflow_exception is None:
                if result > 0:
                    return rfloat.INFINITY
                else:
                    return -rfloat.INFINITY
            else:
                raise OperationError(w_overflow_exception,
                                     space.wrap('value too large'))
        return result
    finally:
        if not user_endptr:
            lltype.free(endptr, flavor='raw')
