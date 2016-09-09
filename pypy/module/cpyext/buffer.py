from rpython.rtyper.lltypesystem import rffi
from rpython.rlib import buffer
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, Py_TPFLAGS_HAVE_NEWBUFFER)
from pypy.module.cpyext.pyobject import PyObject

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_CheckBuffer(space, pyobj):
    """Return 1 if obj supports the buffer interface otherwise 0."""
    as_buffer = pyobj.c_ob_type.c_tp_as_buffer
    flags = pyobj.c_ob_type.c_tp_flags
    if (flags & Py_TPFLAGS_HAVE_NEWBUFFER and as_buffer.c_bf_getbuffer):
        return 1
    return 0



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
