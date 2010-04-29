from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL, Py_ssize_t,\
                                    Py_ssize_tP, build_type_checkers
from pypy.module.cpyext.pyobject import Py_DecRef, PyObject
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.interpreter.error import OperationError
from pypy.objspace.std.sliceobject import W_SliceObject

PySlice_Check, PySlice_CheckExact = build_type_checkers("Slice")

@cpython_api([PyObject, Py_ssize_t, Py_ssize_tP, Py_ssize_tP, Py_ssize_tP, 
                Py_ssize_tP], rffi.INT_real, error=-1)
def PySlice_GetIndicesEx(space, w_slice, length, start_p, stop_p, 
        step_p, slicelength_p):
    """Usable replacement for PySlice_GetIndices().  Retrieve the start,
    stop, and step indices from the slice object slice assuming a sequence of
    length length, and store the length of the slice in slicelength.  Out
    of bounds indices are clipped in a manner consistent with the handling of
    normal slices.
    
    Returns 0 on success and -1 on error with exception set."""
    if not PySlice_Check(space, w_slice):
        PyErr_BadInternalCall(space)
    assert isinstance(w_slice, W_SliceObject)
    start_p[0], stop_p[0], step_p[0], slicelength_p[0] = \
            w_slice.indices4(space, length)
    return 0
