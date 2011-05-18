from pypy.module.cpyext.api import (
    cpython_api, generic_cpy_call, CANNOT_FAIL, CConfig, cpython_struct)
from pypy.rpython.lltypesystem import rffi, lltype

PyInterpreterState = lltype.Ptr(cpython_struct("PyInterpreterState", ()))
PyThreadState = lltype.Ptr(cpython_struct("PyThreadState", [('interp', PyInterpreterState)]))

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

# XXX: might be generally useful
def encapsulator(T, flavor='raw'):
    class MemoryCapsule(object):
        def __init__(self, alloc=True):
            if alloc:
                self.memory = lltype.malloc(T, flavor=flavor)
            else:
                self.memory = lltype.nullptr(T)
        def __del__(self):
            if self.memory:
                lltype.free(self.memory, flavor=flavor)
    return MemoryCapsule

ThreadStateCapsule = encapsulator(PyThreadState.TO)

from pypy.interpreter.executioncontext import ExecutionContext
ExecutionContext.cpyext_threadstate = ThreadStateCapsule(alloc=False)

class InterpreterState(object):
    def __init__(self, space):
        self.interpreter_state = lltype.malloc(PyInterpreterState.TO, flavor='raw', immortal=True)

    def new_thread_state(self):
        capsule = ThreadStateCapsule()
        ts = capsule.memory
        ts.c_interp = self.interpreter_state
        return capsule

    def get_thread_state(self, space):
        ec = space.getexecutioncontext()
        return self._get_thread_state(ec).memory

    def _get_thread_state(self, ec):
        if ec.cpyext_threadstate.memory == lltype.nullptr(PyThreadState.TO):
            ec.cpyext_threadstate = self.new_thread_state()

        return ec.cpyext_threadstate

@cpython_api([], PyThreadState, error=CANNOT_FAIL)
def PyThreadState_Get(space):
    state = space.fromcache(InterpreterState)
    return state.get_thread_state(space)

@cpython_api([PyThreadState], PyThreadState, error=CANNOT_FAIL)
def PyThreadState_Swap(space, tstate):
    """Swap the current thread state with the thread state given by the argument
    tstate, which may be NULL.  The global interpreter lock must be held."""
    # All cpyext calls release and acquire the GIL, so this function has no
    # side-effects
    if tstate:
        return lltype.nullptr(PyThreadState.TO)
    else:
        state = space.fromcache(InterpreterState)
        return state.get_thread_state(space)

@cpython_api([PyThreadState], lltype.Void)
def PyEval_AcquireThread(space, tstate):
    """Acquire the global interpreter lock and set the current thread state to
    tstate, which should not be NULL.  The lock must have been created earlier.
    If this thread already has the lock, deadlock ensues.  This function is not
    available when thread support is disabled at compile time."""
    # All cpyext calls release and acquire the GIL, so this is not necessary.
    pass

@cpython_api([PyThreadState], lltype.Void)
def PyEval_ReleaseThread(space, tstate):
    """Reset the current thread state to NULL and release the global interpreter
    lock.  The lock must have been created earlier and must be held by the current
    thread.  The tstate argument, which must not be NULL, is only used to check
    that it represents the current thread state --- if it isn't, a fatal error is
    reported. This function is not available when thread support is disabled at
    compile time."""
    # All cpyext calls release and acquire the GIL, so this is not necessary.
    pass

PyGILState_STATE = rffi.COpaquePtr('PyGILState_STATE',
                                   typedef='PyGILState_STATE',
                                   compilation_info=CConfig._compilation_info_)

@cpython_api([], PyGILState_STATE, error=CANNOT_FAIL)
def PyGILState_Ensure(space):
    # All cpyext calls release and acquire the GIL, so this is not necessary.
    return 0

@cpython_api([PyGILState_STATE], lltype.Void)
def PyGILState_Release(space, state):
    # All cpyext calls release and acquire the GIL, so this is not necessary.
    return

@cpython_api([], PyInterpreterState, error=CANNOT_FAIL)
def PyInterpreterState_Head(space):
    """Return the interpreter state object at the head of the list of all such objects.
    """
    return space.fromcache(InterpreterState).interpreter_state

@cpython_api([PyInterpreterState], PyInterpreterState, error=CANNOT_FAIL)
def PyInterpreterState_Next(space, interp):
    """Return the next interpreter state object after interp from the list of all
    such objects.
    """
    return lltype.nullptr(PyInterpreterState.TO)
