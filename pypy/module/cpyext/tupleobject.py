from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, Py_ssize_t, CANNOT_FAIL,
                                    build_type_checkers)
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef, register_container
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.objspace.std.tupleobject import W_TupleObject


PyTuple_Check, PyTuple_CheckExact = build_type_checkers("Tuple")

@cpython_api([Py_ssize_t], PyObject)
def PyTuple_New(space, size):
    return space.newtuple([space.w_None] * size)

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyTuple_SetItem(space, w_t, pos, w_obj):
    if not PyTuple_Check(space, w_t):
        # XXX this should also steal a reference, test it!!!
        PyErr_BadInternalCall(space)
    assert isinstance(w_t, W_TupleObject)
    w_t.wrappeditems[pos] = w_obj
    Py_DecRef(space, w_obj) # SetItem steals a reference!
    return 0

@cpython_api([PyObject, Py_ssize_t], PyObject, borrowed=True)
def PyTuple_GetItem(space, w_t, pos):
    if not PyTuple_Check(space, w_t):
        PyErr_BadInternalCall(space)
    assert isinstance(w_t, W_TupleObject)
    w_obj = w_t.wrappeditems[pos]
    register_container(space, w_t)
    return w_obj

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyTuple_GET_SIZE(space, w_t):
    """Return the size of the tuple p, which must be non-NULL and point to a tuple;
    no error checking is performed. """
    assert isinstance(w_t, W_TupleObject)
    return len(w_t.wrappeditems)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyTuple_Size(space, ref):
    """Take a pointer to a tuple object, and return the size of that tuple."""
    if not PyTuple_Check(space, ref):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected tuple object"))
    return PyTuple_GET_SIZE(space, ref)
