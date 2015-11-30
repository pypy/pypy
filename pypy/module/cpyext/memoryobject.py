from pypy.module.cpyext.api import cpython_api, Py_buffer, build_type_checkers
from pypy.module.cpyext.pyobject import PyObject
from rpython.rtyper.lltypesystem import lltype

PyMemoryView_Check, PyMemoryView_CheckExact = build_type_checkers("MemoryView", "w_memoryview")

@cpython_api([PyObject], PyObject)
def PyMemoryView_FromObject(space, w_obj):
    return space.call_method(space.builtin, "memoryview", w_obj)

@cpython_api([PyObject], PyObject)
def PyMemoryView_GET_BASE(space, w_obj):
    # return the obj field of the Py_buffer created by PyMemoryView_GET_BUFFER
    raise NotImplementedError

@cpython_api([PyObject], lltype.Ptr(Py_buffer))
def PyMemoryView_GET_BUFFER(space, obj):
    """Return a pointer to the buffer-info structure wrapped by the given
    object.  The object must be a memoryview instance; this macro doesn't
    check its type, you must do it yourself or you will risk crashes."""
    raise NotImplementedError


