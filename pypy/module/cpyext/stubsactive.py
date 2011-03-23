from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api, Py_ssize_t, CANNOT_FAIL, CConfig
from pypy.module.cpyext.object import FILEP
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.pystate import PyThreadState, PyInterpreterState


@cpython_api([PyObject], FILEP, error=CANNOT_FAIL)
def PyFile_AsFile(space, p):
    """Return the file object associated with p as a FILE*.
    
    If the caller will ever use the returned FILE* object while
    the GIL is released it must also call the PyFile_IncUseCount() and
    PyFile_DecUseCount() functions described below as appropriate."""
    raise NotImplementedError

@cpython_api([PyInterpreterState], PyThreadState, error=CANNOT_FAIL)
def PyThreadState_New(space, interp):
    """Create a new thread state object belonging to the given interpreter object.
    The global interpreter lock need not be held, but may be held if it is
    necessary to serialize calls to this function."""
    raise NotImplementedError

@cpython_api([PyThreadState], lltype.Void)
def PyThreadState_Clear(space, tstate):
    """Reset all information in a thread state object.  The global interpreter lock
    must be held."""
    raise NotImplementedError

@cpython_api([PyThreadState], lltype.Void)
def PyThreadState_Delete(space, tstate):
    """Destroy a thread state object.  The global interpreter lock need not be held.
    The thread state must have been reset with a previous call to
    PyThreadState_Clear()."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def Py_MakePendingCalls(space):
    return 0

