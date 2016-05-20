from rpython.rlib.buffer import Buffer, StringBuffer, SubBuffer
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.api import (
    cpython_api, Py_ssize_t, cpython_struct, bootstrap_function,
    PyObjectFields, PyObject)
from pypy.module.cpyext.pyobject import make_typedescr, Py_DecRef, make_ref
from pypy.module.array.interp_array import ArrayBuffer
from pypy.objspace.std.bufferobject import W_Buffer


class LeakedBuffer(Buffer):
    __slots__ = ['buf','ptr']
    _immutable_ = True

    def __init__(self, buffer):
        if not buffer.readonly:
            raise ValueError("Can only leak a copy of a readonly buffer.")
        self.buf = buffer
        self.readonly = True
        self.ptr = rffi.cast(rffi.VOIDP, rffi.str2charp(self.buf.as_str()))

    def getlength(self):
        return self.buf.getlength()

    def as_str(self):
        return self.buf.as_str()

    def as_str_and_offset_maybe(self):
        return self.buf.as_str_and_offset_maybe()

    def getitem(self, index):
        return self.buf.getitem(index)

    def getslice(self, start, stop, step, size):
        return self.buf.getslice(start, stop, step, size)

    def setitem(self, index, char):
        return self.buf.setitem(index)

    def setslice(self, start, string):
        return self.buf.setslice(start, string)

    def get_raw_address(self):
        return self.ptr


def leak_stringbuffer(buf):
    if isinstance(buf, StringBuffer):
        return LeakedBuffer(buf)
    elif isinstance(buf, SubBuffer):
        leaked = leak_stringbuffer(buf.buffer)
        if leaked is None:
            return leaked
        return SubBuffer(leaked, buf.offset, buf.size)
    else:
        return None


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

def buffer_attach(space, py_obj, w_obj):
    """
    Fills a newly allocated PyBufferObject with the given (str) buffer object.
    """
    py_buf = rffi.cast(PyBufferObject, py_obj)
    py_buf.c_b_offset = 0
    rffi.setintfield(py_buf, 'c_b_readonly', 1)
    rffi.setintfield(py_buf, 'c_b_hash', -1)

    assert isinstance(w_obj, W_Buffer)
    buf = w_obj.buf

    w_obj.buf = buf = leak_stringbuffer(buf) or buf
    # Now, if it was backed by a StringBuffer, it is now a LeakedBuffer.
    # We deliberately copy the string so that we can have a pointer to it,
    # and we make it accessible in the buffer through get_raw_address(), so that
    # we can reuse it elsewhere in the C API.

    if isinstance(buf, SubBuffer):
        py_buf.c_b_offset = buf.offset
        buf = buf.buffer

    if isinstance(buf, LeakedBuffer):
        py_buf.c_b_base = lltype.nullptr(PyObject.TO)
        py_buf.c_b_ptr = buf.get_raw_address()
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


@cpython_api([PyObject], lltype.Void, header=None)
def buffer_dealloc(space, py_obj):
    py_buf = rffi.cast(PyBufferObject, py_obj)
    if py_buf.c_b_base:
        Py_DecRef(space, py_buf.c_b_base)
    else:
        rffi.free_charp(rffi.cast(rffi.CCHARP, py_buf.c_b_ptr))
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)
