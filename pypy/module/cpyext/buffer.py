from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, Py_TPFLAGS_HAVE_NEWBUFFER)
from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.bytesobject import PyBytesObject

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyObject_CheckBuffer(space, pyobj):
    """Return 1 if obj supports the buffer interface otherwise 0."""
    as_buffer = pyobj.c_ob_type.c_tp_as_buffer
    flags = pyobj.c_ob_type.c_tp_flags
    if (flags & Py_TPFLAGS_HAVE_NEWBUFFER and as_buffer.c_bf_getbuffer):
        return 1
    name = rffi.charp2str(pyobj.c_ob_type.c_tp_name)
    if  name in ('str', 'bytes'):
        # XXX remove once wrapper of __buffer__ -> bf_getbuffer works
        return 1
    return 0  

    
