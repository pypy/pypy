from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, Py_buffer
from pypy.module.cpyext.pyobject import PyObject, from_ref
from pypy.module.cpyext.buffer import CBuffer
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.__builtin__.interp_memoryview import W_MemoryView

@cpython_api([PyObject], PyObject)
def PyMemoryView_FromObject(space, w_obj):
    return space.call_method(space.builtin, "memoryview", w_obj)

@cpython_api([lltype.Ptr(Py_buffer)], PyObject)
def PyMemoryView_FromBuffer(space, view):
    """Create a memoryview object wrapping the given buffer structure view.
    The memoryview object then owns the buffer represented by view, which
    means you shouldn't try to call PyBuffer_Release() yourself: it
    will be done on deallocation of the memoryview object."""
    if not view.c_buf:
        msg = "cannot make memory view from a buffer with a NULL data pointer"
        raise OperationError(space.w_ValueError, space.wrap(msg))
    w_obj = from_ref(space, view.c_obj)
    buf = CBuffer(space, view.c_buf, view.c_len, w_obj)
    return space.wrap(W_MemoryView(buf))
