from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject

@cpython_api([lltype.Float], lltype.Ptr(PyObject))
def PyFloat_FromDouble(space, value):
    return space.wrap(value)
