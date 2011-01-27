from pypy.module.cpyext.api import cpython_api, generic_cpy_call, CANNOT_FAIL,\
        cpython_struct
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
def PyThreadState_Get(space, ):
    state = space.fromcache(InterpreterState)
    return state.get_thread_state(space)

@cpython_api([], PyInterpreterState, error=CANNOT_FAIL)
def PyInterpreterState_Head(space, ):
    """Return the interpreter state object at the head of the list of all such objects.
    """
    return space.fromcache(InterpreterState).interpreter_state

@cpython_api([PyInterpreterState], PyInterpreterState, error=CANNOT_FAIL)
def PyInterpreterState_Next(space, interp):
    """Return the next interpreter state object after interp from the list of all
    such objects.
    """
    return lltype.nullptr(PyInterpreterState.TO)
