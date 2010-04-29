from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def Py_IsInitialized(space):
    return 1
