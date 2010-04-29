from pypy.module.cpyext.api import cpython_api, generic_cpy_call, CANNOT_FAIL,\
        cpython_struct
from pypy.rpython.lltypesystem import rffi, lltype


PyThreadState = lltype.Ptr(cpython_struct("PyThreadState", ()))
PyInterpreterState = lltype.Ptr(cpython_struct("PyInterpreterState", ()))

@cpython_api([], PyThreadState, error=CANNOT_FAIL)
def PyEval_SaveThread(space):
    """Release the global interpreter lock (if it has been created and thread
    support is enabled) and reset the thread state to NULL, returning the
    previous thread state (which is not NULL except in PyPy).  If the lock has been created,
    the current thread must have acquired it.  (This function is available even
    when thread support is disabled at compile time.)"""
    if rffi.aroundstate.before:
        rffi.aroundstate.before()
    return lltype.nullptr(PyThreadState.TO)

@cpython_api([PyThreadState], lltype.Void)
def PyEval_RestoreThread(space, tstate):
    """Acquire the global interpreter lock (if it has been created and thread
    support is enabled) and set the thread state to tstate, which must not be
    NULL.  If the lock has been created, the current thread must not have
    acquired it, otherwise deadlock ensues.  (This function is available even
    when thread support is disabled at compile time.)"""
    if rffi.aroundstate.after:
        rffi.aroundstate.after()

@cpython_api([], lltype.Void)
def PyEval_InitThreads(space):
    return

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyEval_ThreadsInitialized(space):
    return 1


