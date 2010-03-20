from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject

@cpython_api([rffi.LONG], PyObject)
def PyBool_FromLong(space, value):
    if value != 0:
        return space.w_True
    return space.w_False
