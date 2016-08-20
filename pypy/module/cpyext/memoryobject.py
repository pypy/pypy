from pypy.module.cpyext.api import (cpython_api, Py_buffer, CANNOT_FAIL,
                                    build_type_checkers)
from pypy.module.cpyext.pyobject import PyObject
from rpython.rtyper.lltypesystem import lltype

PyMemoryView_Check, PyMemoryView_CheckExact = build_type_checkers("MemoryView", "w_memoryview")

@cpython_api([PyObject], PyObject)
def PyMemoryView_FromObject(space, w_obj):
    return space.call_method(space.builtin, "memoryview", w_obj)

@cpython_api([PyObject], PyObject)
def PyMemoryView_GET_BASE(space, w_obj):
    # return the obj field of the Py_buffer created by PyMemoryView_GET_BUFFER
    raise NotImplementedError('PyMemoryView_GET_BUFFER')

@cpython_api([PyObject], lltype.Ptr(Py_buffer), error=CANNOT_FAIL)
def PyMemoryView_GET_BUFFER(space, w_obj):
    """Return a pointer to the buffer-info structure wrapped by the given
    object.  The object must be a memoryview instance; this macro doesn't
    check its type, you must do it yourself or you will risk crashes."""
    view = lltype.malloc(Py_buffer, flavor='raw', zero=True)
    # TODO - fill in fields
    '''
    view.c_buf = buf
    view.c_len = length
    view.c_obj = obj
    Py_IncRef(space, obj)
    view.c_itemsize = 1
    rffi.setintfield(view, 'c_readonly', readonly)
    rffi.setintfield(view, 'c_ndim', 0)
    view.c_format = lltype.nullptr(rffi.CCHARP.TO)
    view.c_shape = lltype.nullptr(Py_ssize_tP.TO)
    view.c_strides = lltype.nullptr(Py_ssize_tP.TO)
    view.c_suboffsets = lltype.nullptr(Py_ssize_tP.TO)
    view.c_internal = lltype.nullptr(rffi.VOIDP.TO)
    ''' 
    return view


