from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.api import cpython_api, PyObject

@cpython_api([rffi.LONG], PyObject)
def PyBool_FromLong(space, value):
    if value != 0:
        return space.w_True
    return space.w_False
