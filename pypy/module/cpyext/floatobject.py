from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref

@cpython_api([lltype.Float], PyObject)
def PyFloat_FromDouble(space, value):
    return space.wrap(value)
