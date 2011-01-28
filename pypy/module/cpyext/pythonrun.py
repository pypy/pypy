from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.state import State

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def Py_IsInitialized(space):
    return 1

@cpython_api([], rffi.CCHARP, error=CANNOT_FAIL)
def Py_GetProgramName(space):
    """
    Return the program name set with Py_SetProgramName(), or the default.
    The returned string points into static storage; the caller should not modify its
    value."""
    return space.fromcache(State).get_programname()

