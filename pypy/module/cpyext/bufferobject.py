from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, Py_ssize_t, cpython_struct, bootstrap_function,
    PyObjectFields, PyObject)
from pypy.module.cpyext.pyobject import make_typedescr, Py_DecRef, make_ref
from pypy.interpreter.buffer import Buffer, StringBuffer, SubBuffer
from pypy.interpreter.error import OperationError
from pypy.module.array.interp_array import ArrayBuffer


PyBufferObjectStruct = lltype.ForwardReference()
PyBufferObject = lltype.Ptr(PyBufferObjectStruct)
PyBufferObjectFields = PyObjectFields + (
    ("b_base", PyObject),
    ("b_ptr", rffi.VOIDP),
    ("b_size", Py_ssize_t),
    ("b_offset", Py_ssize_t),
    ("b_readonly", rffi.INT),
    ("b_hash", rffi.LONG),
    )

cpython_struct("PyBufferObject", PyBufferObjectFields, PyBufferObjectStruct)

@bootstrap_function
def init_bufferobject(space):
    "Type description of PyBufferObject"
    make_typedescr(space.gettypefor(Buffer).instancetypedef,
                   basestruct=PyBufferObject.TO,
                   attach=buffer_attach,
                   dealloc=buffer_dealloc,
                   realize=buffer_realize)

def buffer_attach(space, py_obj, w_obj):
    """
    Fills a newly allocated PyBufferObject with the given (str) buffer object.
    """
    py_buf = rffi.cast(PyBufferObject, py_obj)
    py_buf.c_b_offset = 0
    rffi.setintfield(py_buf, 'c_b_readonly', 1)
    rffi.setintfield(py_buf, 'c_b_hash', -1)

    if isinstance(w_obj, SubBuffer):
        py_buf.c_b_offset = w_obj.offset
        w_obj = w_obj.buffer

    # If w_obj already allocated a fixed buffer, use it, and keep a
    # reference to w_obj.
    # Otherwise, b_base stays NULL, and we own the b_ptr.

    if isinstance(w_obj, StringBuffer):
        py_buf.c_b_base = lltype.nullptr(PyObject.TO)
        py_buf.c_b_ptr = rffi.cast(rffi.VOIDP, rffi.str2charp(w_obj.value))
        py_buf.c_b_size = w_obj.getlength()
    elif isinstance(w_obj, ArrayBuffer):
        w_base = w_obj.array
        py_buf.c_b_base = make_ref(space, w_base)
        py_buf.c_b_ptr = rffi.cast(rffi.VOIDP, w_obj.array._charbuf_start())
        py_buf.c_b_size = w_obj.getlength()
    else:
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "buffer flavor not supported"))


def buffer_realize(space, py_obj):
    """
    Creates the buffer in the PyPy interpreter from a cpyext representation.
    """
    raise OperationError(space.w_NotImplementedError, space.wrap(
        "Don't know how to realize a buffer"))


@cpython_api([PyObject], lltype.Void, external=False)
def buffer_dealloc(space, py_obj):
    py_buf = rffi.cast(PyBufferObject, py_obj)
    if py_buf.c_b_base:
        Py_DecRef(space, py_buf.c_b_base)
    else:
        rffi.free_charp(rffi.cast(rffi.CCHARP, py_buf.c_b_ptr))
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)
