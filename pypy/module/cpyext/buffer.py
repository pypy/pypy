from pypy.interpreter.error import oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import buffer
from rpython.rlib.rarithmetic import widen
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, Py_buffer)
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef

def _IsFortranContiguous(view):
    ndim = widen(view.c_ndim)
    if ndim == 0:
        return 1
    if not view.c_strides:
        return ndim == 1
    sd = view.c_itemsize
    if ndim == 1:
        return view.c_shape[0] == 1 or sd == view.c_strides[0]
    for i in range(view.c_ndim):
        dim = view.c_shape[i]
        if dim == 0:
            return 1
        if view.c_strides[i] != sd:
            return 0
        sd *= dim
    return 1

def _IsCContiguous(view):
    ndim = widen(view.c_ndim)
    if ndim == 0:
        return 1
    if not view.c_strides:
        return ndim == 1
    sd = view.c_itemsize
    if ndim == 1:
        return view.c_shape[0] == 1 or sd == view.c_strides[0]
    for i in range(ndim - 1, -1, -1):
        dim = view.c_shape[i]
        if dim == 0:
            return 1
        if view.c_strides[i] != sd:
            return 0
        sd *= dim
    return 1
        

@cpython_api([lltype.Ptr(Py_buffer), lltype.Char], rffi.INT_real, error=CANNOT_FAIL)
def PyBuffer_IsContiguous(space, view, fort):
    """Return 1 if the memory defined by the view is C-style (fortran is
    'C') or Fortran-style (fortran is 'F') contiguous or either one
    (fortran is 'A').  Return 0 otherwise."""
    # traverse the strides, checking for consistent stride increases from
    # right-to-left (c) or left-to-right (fortran). Copied from cpython
    if not view.c_suboffsets:
        return 0
    if (fort == 'C'):
        return _IsCContiguous(view)
    elif (fort == 'F'):
        return _IsFortranContiguous(view)
    elif (fort == 'A'):
        return (_IsCContiguous(view) or _IsFortranContiguous(view))
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
