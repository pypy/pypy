
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import (cpython_api, PyObject, CANNOT_FAIL,
                                    build_type_checkers, Py_ssize_t)


PyInt_Check, PyInt_CheckExact = build_type_checkers("Int")

@cpython_api([lltype.Signed], PyObject)
def PyInt_FromLong(space, ival):
    """Create a new integer object with a value of ival.
    
    """
    return space.wrap(ival)

@cpython_api([PyObject], lltype.Signed, error=-1)
def PyInt_AsLong(space, w_obj):
    """Will first attempt to cast the object to a PyIntObject, if it is not
    already one, and then return its value. If there is an error, -1 is
    returned, and the caller should check PyErr_Occurred() to find out whether
    there was an error, or whether the value just happened to be -1."""
    if w_obj is None:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    return space.int_w(space.int(w_obj))

@cpython_api([PyObject], lltype.Unsigned, error=-1)
def PyInt_AsUnsignedLong(space, w_obj):
    """Return a C unsigned long representation of the contents of pylong.
    If pylong is greater than ULONG_MAX, an OverflowError is
    raised."""
    if w_obj is None:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    return space.uint_w(space.int(w_obj))

@cpython_api([PyObject], lltype.Signed, error=CANNOT_FAIL)
def PyInt_AS_LONG(space, w_int):
    """Return the value of the object w_int. No error checking is performed."""
    return space.int_w(w_int)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyInt_AsSsize_t(space, w_obj):
    """Will first attempt to cast the object to a PyIntObject or
    PyLongObject, if it is not already one, and then return its value as
    Py_ssize_t.
    """
    if w_obj is None:
        raise OperationError(space.w_TypeError,
                             space.wrap("an integer is required, got NULL"))
    return space.int_w(w_obj) # XXX this is wrong on win64

@cpython_api([Py_ssize_t], PyObject)
def PyInt_FromSsize_t(space, ival):
    """Create a new integer object with a value of ival. If the value is larger
    than LONG_MAX or smaller than LONG_MIN, a long integer object is
    returned.
    """
    return space.wrap(ival) # XXX this is wrong on win64
