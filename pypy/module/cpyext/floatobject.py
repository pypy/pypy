from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    CANNOT_FAIL, cpython_api, PyObject, build_type_checkers, CONST_STRING)
from pypy.interpreter.error import OperationError
from rpython.rlib.rstruct import runpack

PyFloat_Check, PyFloat_CheckExact = build_type_checkers("Float")

@cpython_api([lltype.Float], PyObject)
def PyFloat_FromDouble(space, value):
    return space.wrap(value)

@cpython_api([PyObject], lltype.Float, error=-1)
def PyFloat_AsDouble(space, w_obj):
    return space.float_w(space.float(w_obj))

@cpython_api([PyObject], lltype.Float, error=CANNOT_FAIL)
def PyFloat_AS_DOUBLE(space, w_float):
    """Return a C double representation of the contents of w_float, but
    without error checking."""
    return space.float_w(w_float)

@cpython_api([PyObject], PyObject)
def PyNumber_Float(space, w_obj):
    """
    Returns the o converted to a float object on success, or NULL on failure.
    This is the equivalent of the Python expression float(o)."""
    return space.call_function(space.w_float, w_obj)

@cpython_api([PyObject, rffi.CCHARPP], PyObject)
def PyFloat_FromString(space, w_obj, _):
    """Create a PyFloatObject object based on the string value in str, or
    NULL on failure.  The pend argument is ignored.  It remains only for
    backward compatibility."""
    return space.call_function(space.w_float, w_obj)

@cpython_api([CONST_STRING, rffi.INT_real], rffi.DOUBLE, error=-1.0)
def _PyFloat_Unpack4(space, ptr, le):
    input = rffi.charpsize2str(ptr, 4)
    if rffi.cast(lltype.Signed, le):
        return runpack.runpack("<f", input)
    else:
        return runpack.runpack(">f", input)

@cpython_api([CONST_STRING, rffi.INT_real], rffi.DOUBLE, error=-1.0)
def _PyFloat_Unpack8(space, ptr, le):
    input = rffi.charpsize2str(ptr, 8)
    if rffi.cast(lltype.Signed, le):
        return runpack.runpack("<d", input)
    else:
        return runpack.runpack(">d", input)

