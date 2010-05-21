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

@cpython_api([PyThreadState], PyThreadState, error=CANNOT_FAIL)
def PyThreadState_Swap(space, tstate):
    """Swap the current thread state with the thread state given by the argument
    tstate, which may be NULL.  The global interpreter lock must be held."""
    raise NotImplementedError

@cpython_api([PyThreadState], lltype.Void)
def PyEval_AcquireThread(space, tstate):
    """Acquire the global interpreter lock and set the current thread state to
    tstate, which should not be NULL.  The lock must have been created earlier.
    If this thread already has the lock, deadlock ensues.  This function is not
    available when thread support is disabled at compile time."""
    raise NotImplementedError

@cpython_api([PyThreadState], lltype.Void)
def PyEval_ReleaseThread(space, tstate):
    """Reset the current thread state to NULL and release the global interpreter
    lock.  The lock must have been created earlier and must be held by the current
    thread.  The tstate argument, which must not be NULL, is only used to check
    that it represents the current thread state --- if it isn't, a fatal error is
    reported. This function is not available when thread support is disabled at
    compile time."""
    raise NotImplementedError

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def Py_MakePendingCalls(space):
    return 0

PyGILState_STATE = rffi.COpaquePtr('PyGILState_STATE',
                                   typedef='PyGILState_STATE',
                                   compilation_info=CConfig._compilation_info_)

@cpython_api([], PyGILState_STATE, error=CANNOT_FAIL)
def PyGILState_Ensure(space):
    return 0

@cpython_api([PyGILState_STATE], lltype.Void)
def PyGILState_Release(space, state):
    return

