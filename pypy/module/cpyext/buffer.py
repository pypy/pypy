from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.api import (
    cpython_api, Py_buffer, Py_ssize_t, Py_ssize_tP, CONST_STRINGP, cts,
    generic_cpy_call,
    PyBUF_WRITABLE, PyBUF_FORMAT, PyBUF_ND, PyBUF_STRIDES)
from pypy.module.cpyext.pyobject import PyObject, incref

@cpython_api([PyObject, CONST_STRINGP, Py_ssize_tP], rffi.INT_real, error=-1)
def PyObject_AsCharBuffer(space, obj, bufferp, sizep):
    """Returns a pointer to a read-only memory location usable as
    character-based input.  The obj argument must support the single-segment
    character buffer interface.  On success, returns 0, sets buffer to the
    memory location and size to the buffer length.  Returns -1 and sets a
    TypeError on error.
    """
    pto = obj.c_ob_type
    pb = pto.c_tp_as_buffer
    if not (pb and pb.c_bf_getreadbuffer and pb.c_bf_getsegcount):
        raise oefmt(space.w_TypeError, "expected a character buffer object")
    if generic_cpy_call(space, pb.c_bf_getsegcount,
                        obj, lltype.nullptr(Py_ssize_tP.TO)) != 1:
        raise oefmt(space.w_TypeError,
                    "expected a single-segment buffer object")
    size = generic_cpy_call(space, pb.c_bf_getcharbuffer,
                            obj, 0, bufferp)
    if size < 0:
        return -1
    sizep[0] = size
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
        incref(space, obj)
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
