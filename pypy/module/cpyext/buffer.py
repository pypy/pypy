from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import buffer
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, Py_buffer)
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef

@cpython_api([lltype.Ptr(Py_buffer), lltype.Char], rffi.INT_real, error=CANNOT_FAIL)
def PyBuffer_IsContiguous(space, view, fortran):
    """Return 1 if the memory defined by the view is C-style (fortran is
    'C') or Fortran-style (fortran is 'F') contiguous or either one
    (fortran is 'A').  Return 0 otherwise."""
    # PyPy only supports contiguous Py_buffers for now.
    return 1

class CBufferMixin(object):
    _mixin_ = True

    def __init__(self, space, c_buf, c_len, w_obj):
        self.space = space
        self.c_buf = c_buf
        self.c_len = c_len
        self.w_obj = w_obj

    def destructor(self):
        assert isinstance(self, CBufferMixin)
        Py_DecRef(self.space, self.w_obj)

    def getlength(self):
        return self.c_len

    def getitem(self, index):
        return self.c_buf[index]

    def as_str(self):
        return rffi.charpsize2str(rffi.cast(rffi.CCHARP, self.c_buf),
                                  self.c_len)
        
class CBuffer(CBufferMixin, buffer.Buffer):
    def __del__(self):
        CBufferMixin.destructor(self)
