from pypy.module.cpyext.api import (cpython_api, Py_buffer, CANNOT_FAIL,
                                    build_type_checkers, Py_ssize_tP)
from pypy.module.cpyext.pyobject import PyObject, as_pyobj, incref
from rpython.rtyper.lltypesystem import lltype, rffi
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
    try:
        view.c_buf = rffi.cast(rffi.VOIDP, w_obj.buf.get_raw_address())
    except ValueError:
        return view
    view.c_len = w_obj.getlength()
    view.c_obj = as_pyobj(space, w_obj)
    incref(space, view.c_obj)
    view.c_itemsize = w_obj.buf.getitemsize()
    rffi.setintfield(view, 'c_readonly', w_obj.buf.readonly)
    ndim = w_obj.buf.getndim()
    rffi.setintfield(view, 'c_ndim', ndim)
    view.c_format = rffi.str2charp(w_obj.buf.getformat())
    view.c_shape = lltype.malloc(Py_ssize_tP.TO, ndim, flavor='raw')
    view.c_strides = lltype.malloc(Py_ssize_tP.TO, ndim, flavor='raw')
    shape = w_obj.buf.getshape()
    strides = w_obj.buf.getstrides()
    for i in range(ndim):
        view.c_shape[i] = shape[i]
        view.c_strides[i] = strides[i]
    view.c_suboffsets = lltype.nullptr(Py_ssize_tP.TO)
    view.c_internal = lltype.nullptr(rffi.VOIDP.TO)
    return view


