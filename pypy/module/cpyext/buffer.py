from pypy.interpreter.error import oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import buffer
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, Py_buffer)
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef

# PyObject_GetBuffer has been removed, it is defined in abstract.c
# PyObject_CheckBuffer is also already defined

@cpython_api([lltype.Ptr(Py_buffer), lltype.Char], rffi.INT_real, error=CANNOT_FAIL)
def PyBuffer_IsContiguous(space, view, fortran):
    """Return 1 if the memory defined by the view is C-style (fortran is
    'C') or Fortran-style (fortran is 'F') contiguous or either one
    (fortran is 'A').  Return 0 otherwise."""
    # PyPy only supports contiguous Py_buffers for now.
    return 1

class CBuffer(buffer.Buffer):

    _immutable_ = True

    def __init__(self, space, c_buf, c_len, c_obj):
        self.space = space
        self.c_buf = c_buf
        self.c_len = c_len
        self.c_obj = c_obj

    def __del__(self):
        Py_DecRef(self.space, self.c_obj)

    def getlength(self):
        return self.c_len

    def getitem(self, index):
        return self.c_buf[index]

    def as_str(self):
        return rffi.charpsize2str(rffi.cast(rffi.CCHARP, self.c_buf),
                                  self.c_len)
