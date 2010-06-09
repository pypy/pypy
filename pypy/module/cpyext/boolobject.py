from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.gateway import (
    cpython_api, CANNOT_FAIL)
from pypy.module.cpyext.api import PyObject, build_type_checkers

# Inheriting from bool isn't actually possible.
PyBool_Check = build_type_checkers("Bool")[1]

@cpython_api([rffi.LONG], PyObject)
def PyBool_FromLong(space, value):
    if value != 0:
        return space.w_True
    return space.w_False
