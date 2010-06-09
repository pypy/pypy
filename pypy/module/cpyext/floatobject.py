from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.gateway import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.api import PyObject, build_type_checkers
from pypy.interpreter.error import OperationError

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
    return space.float(w_obj)
