from pypy.module.cpyext.api import (cpython_api, Py_buffer, CANNOT_FAIL,
                         Py_MAX_FMT, Py_MAX_NDIMS, build_type_checkers, Py_ssize_tP)
from pypy.module.cpyext.pyobject import PyObject, make_ref, incref
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.objspace.std.memoryobject import W_MemoryView

from pypy.interpreter.error import oefmt
from pypy.module.cpyext.pyobject import PyObject, from_ref
from pypy.module.cpyext.buffer import CBuffer
from pypy.objspace.std.memoryobject import W_MemoryView
PyMemoryView_Check, PyMemoryView_CheckExact = build_type_checkers("MemoryView", "w_memoryview")

@cpython_api([PyObject], PyObject)
def PyMemoryView_FromObject(space, w_obj):
    return space.call_method(space.builtin, "memoryview", w_obj)

@cpython_api([PyObject], PyObject)
def PyMemoryView_GET_BASE(space, w_obj):
    # return the obj field of the Py_buffer created by PyMemoryView_GET_BUFFER
    # XXX needed for numpy on py3k
    raise NotImplementedError('PyMemoryView_GET_BUFFER')

@cpython_api([PyObject], lltype.Ptr(Py_buffer), error=CANNOT_FAIL)
def PyMemoryView_GET_BUFFER(space, w_obj):
    """Return a pointer to the buffer-info structure wrapped by the given
    object.  The object must be a memoryview instance; this macro doesn't
    check its type, you must do it yourself or you will risk crashes."""
    view = lltype.malloc(Py_buffer, flavor='raw', zero=True)
    if not isinstance(w_obj, W_MemoryView):
        return view
    ndim = w_obj.buf.getndim()
    if ndim >= Py_MAX_NDIMS:
        # XXX warn?
        return view
    try:
        view.c_buf = rffi.cast(rffi.VOIDP, w_obj.buf.get_raw_address())
        view.c_obj = make_ref(space, w_obj)
        rffi.setintfield(view, 'c_readonly', w_obj.buf.readonly)
        isstr = False
    except ValueError:
        w_s = w_obj.descr_tobytes(space)
        view.c_obj = make_ref(space, w_s)
        rffi.setintfield(view, 'c_readonly', 1)
        isstr = True
    view.c_len = w_obj.getlength()
    view.c_itemsize = w_obj.buf.getitemsize()
    rffi.setintfield(view, 'c_ndim', ndim)
    view.c_format = rffi.cast(rffi.CCHARP, view.c__format)
    view.c_shape = rffi.cast(Py_ssize_tP, view.c__shape)
    view.c_strides = rffi.cast(Py_ssize_tP, view.c__strides)
    fmt = w_obj.buf.getformat()
    n = Py_MAX_FMT - 1 # NULL terminated buffer
    if len(fmt) > n:
        ### WARN?
        pass
    else:
        n = len(fmt)
    for i in range(n):
        if ord(fmt[i]) > 255:
            view.c_format[i] = '*'
        else:
            view.c_format[i] = fmt[i]
    view.c_format[n] = '\x00'        
    shape = w_obj.buf.getshape()
    strides = w_obj.buf.getstrides()
    for i in range(ndim):
        view.c_shape[i] = shape[i]
        view.c_strides[i] = strides[i]
    view.c_suboffsets = lltype.nullptr(Py_ssize_tP.TO)
    view.c_internal = lltype.nullptr(rffi.VOIDP.TO)
    return view

@cpython_api([lltype.Ptr(Py_buffer)], PyObject)
def PyMemoryView_FromBuffer(space, view):
    """Create a memoryview object wrapping the given buffer structure view.
    The memoryview object then owns the buffer represented by view, which
    means you shouldn't try to call PyBuffer_Release() yourself: it
    will be done on deallocation of the memoryview object."""
    if not view.c_buf:
        raise oefmt(space.w_ValueError,
                    "cannot make memory view from a buffer with a NULL data "
                    "pointer")
    buf = CBuffer(space, view.c_buf, view.c_len, view.c_obj)
    return space.wrap(W_MemoryView(buf))
