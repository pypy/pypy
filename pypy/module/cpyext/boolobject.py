from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject

@cpython_api([PyObject], rffi.INT)
def PyBool_Check(space, w_obj):
    if space.eq_w(space.type(w_obj), space.w_bool):
        return 1
    return 0

@cpython_api([rffi.LONG], PyObject)
def PyBool_FromLong(space, value):
    if value != 0:
        return space.w_True
    return space.w_False
