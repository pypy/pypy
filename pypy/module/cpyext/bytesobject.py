from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api

@cpython_api([PyObject], PyObject)
def PyBytes_FromObject(space, w_obj):
    """Return the bytes representation of object obj that implements
    the buffer protocol."""
    if space.is_w(space.type(w_obj), space.w_bytes):
        return w_obj
    buffer = space.buffer_w(w_obj)
    return space.wrapbytes(buffer.as_str())
    

