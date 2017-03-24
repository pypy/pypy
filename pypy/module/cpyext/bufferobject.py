from rpython.rlib.buffer import StringBuffer, SubBuffer
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.api import (
    cpython_api, Py_ssize_t, cpython_struct, bootstrap_function, slot_function,
    PyObjectFields, PyObject)
from pypy.module.cpyext.pyobject import make_typedescr, Py_DecRef, make_ref
from pypy.module.array.interp_array import ArrayBuffer
from pypy.objspace.std.bufferobject import W_Buffer


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
    make_typedescr(space.w_buffer.layout.typedef,
                   basestruct=PyBufferObject.TO,
                   attach=buffer_attach,
                   dealloc=buffer_dealloc,
                   realize=buffer_realize)

def buffer_attach(space, py_obj, w_obj, w_userdata=None):
    """
    Fills a newly allocated PyBufferObject with the given (str) buffer object.
    """
    py_buf = rffi.cast(PyBufferObject, py_obj)
    py_buf.c_b_offset = 0
    rffi.setintfield(py_buf, 'c_b_readonly', 1)
    rffi.setintfield(py_buf, 'c_b_hash', -1)

    assert isinstance(w_obj, W_Buffer)
    buf = w_obj.buf

    if isinstance(buf, SubBuffer):
        py_buf.c_b_offset = buf.offset
        buf = buf.buffer

    # If buf already allocated a fixed buffer, use it, and keep a
    # reference to buf.
    # Otherwise, b_base stays NULL, and we own the b_ptr.

    if isinstance(buf, StringBuffer):
        py_buf.c_b_base = lltype.nullptr(PyObject.TO)
        py_buf.c_b_ptr = rffi.cast(rffi.VOIDP, rffi.str2charp(buf.value))
        py_buf.c_b_size = buf.getlength()
    elif isinstance(buf, ArrayBuffer):
        w_base = buf.array
        py_buf.c_b_base = make_ref(space, w_base)
        py_buf.c_b_ptr = rffi.cast(rffi.VOIDP, buf.array._charbuf_start())
        py_buf.c_b_size = buf.getlength()
    else:
        raise oefmt(space.w_NotImplementedError, "buffer flavor not supported")


def buffer_realize(space, py_obj):
    """
    Creates the buffer in the PyPy interpreter from a cpyext representation.
    """
    raise oefmt(space.w_NotImplementedError,
                "Don't know how to realize a buffer")


@slot_function([PyObject], lltype.Void)
def buffer_dealloc(space, py_obj):
    py_buf = rffi.cast(PyBufferObject, py_obj)
    if py_buf.c_b_base:
        Py_DecRef(space, py_buf.c_b_base)
    else:
        rffi.free_charp(rffi.cast(rffi.CCHARP, py_buf.c_b_ptr))
    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)
