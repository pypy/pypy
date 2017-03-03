from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, Py_TPFLAGS_HAVE_NEWBUFFER, cts, Py_buffer,
    Py_ssize_t, Py_ssize_tP, generic_cpy_call,
    PyBUF_WRITABLE, PyBUF_FORMAT, PyBUF_ND, PyBUF_STRIDES)
from pypy.module.cpyext.pyobject import PyObject, Py_IncRef, Py_DecRef

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_CheckBuffer(space, pyobj):
    """Return 1 if obj supports the buffer interface otherwise 0."""
    as_buffer = pyobj.c_ob_type.c_tp_as_buffer
    flags = pyobj.c_ob_type.c_tp_flags
    if (flags & Py_TPFLAGS_HAVE_NEWBUFFER and as_buffer.c_bf_getbuffer):
        return 1
    return 0

@cpython_api([lltype.Ptr(Py_buffer), PyObject, rffi.VOIDP, Py_ssize_t,
              lltype.Signed, lltype.Signed], rffi.INT, error=-1)
def PyBuffer_FillInfo(space, view, obj, buf, length, readonly, flags):
    """
    Fills in a buffer-info structure correctly for an exporter that can only
    share a contiguous chunk of memory of "unsigned bytes" of the given
    length. Returns 0 on success and -1 (with raising an error) on error.
    """
    if flags & PyBUF_WRITABLE and readonly:
        raise oefmt(space.w_ValueError, "Object is not writable")
    view.c_buf = buf
    view.c_len = length
    view.c_obj = obj
    if obj:
        Py_IncRef(space, obj)
    view.c_itemsize = 1
    rffi.setintfield(view, 'c_readonly', readonly)
    rffi.setintfield(view, 'c_ndim', 1)
    view.c_format = lltype.nullptr(rffi.CCHARP.TO)
    if (flags & PyBUF_FORMAT) == PyBUF_FORMAT:
        view.c_format = rffi.str2charp("B")
    view.c_shape = lltype.nullptr(Py_ssize_tP.TO)
    if (flags & PyBUF_ND) == PyBUF_ND:
        view.c_shape = rffi.cast(Py_ssize_tP, view.c__shape)
        view.c_shape[0] = view.c_len
    view.c_strides = lltype.nullptr(Py_ssize_tP.TO)
    if (flags & PyBUF_STRIDES) == PyBUF_STRIDES:
        view.c_strides = rffi.cast(Py_ssize_tP, view.c__strides)
        view.c_strides[0] = view.c_itemsize
    view.c_suboffsets = lltype.nullptr(Py_ssize_tP.TO)
    view.c_internal = lltype.nullptr(rffi.VOIDP.TO)

    return 0


@cpython_api([lltype.Ptr(Py_buffer)], lltype.Void, error=CANNOT_FAIL)
def PyBuffer_Release(space, view):
    """
    Release the buffer view. This should be called when the buffer is
    no longer being used as it may free memory from it
    """
    obj = view.c_obj
    if not obj:
        return
    assert obj.c_ob_type
    as_buffer = obj.c_ob_type.c_tp_as_buffer
    if as_buffer:
        func = as_buffer.c_bf_releasebuffer
        if func:
            generic_cpy_call(space, func, obj, view)
    Py_DecRef(space, obj)
    view.c_obj = lltype.nullptr(PyObject.TO)
    # XXX do other fields leak memory?
