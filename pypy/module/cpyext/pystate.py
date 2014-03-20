from pypy.module.cpyext.api import (
    cpython_api, generic_cpy_call, CANNOT_FAIL, CConfig, cpython_struct)
from pypy.module.cpyext.pyobject import PyObject, Py_DecRef, make_ref, from_ref
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rthread

PyInterpreterStateStruct = lltype.ForwardReference()
PyInterpreterState = lltype.Ptr(PyInterpreterStateStruct)
cpython_struct(
    "PyInterpreterState",
    [('next', PyInterpreterState)],
    PyInterpreterStateStruct)
PyThreadState = lltype.Ptr(cpython_struct(
    "PyThreadState",
    [('interp', PyInterpreterState),
     ('dict', PyObject),
     ]))

class NoThreads(Exception):
    pass

@cpython_api([], PyThreadState, error=CANNOT_FAIL)
def PyEval_SaveThread(space):
    """Release the global interpreter lock (if it has been created and thread
    support is enabled) and reset the thread state to NULL, returning the
    previous thread state.  If the lock has been created,
    the current thread must have acquired it.  (This function is available even
    when thread support is disabled at compile time.)"""
    state = space.fromcache(InterpreterState)
    tstate = state.swap_thread_state(
        space, lltype.nullptr(PyThreadState.TO))
    if rffi.aroundstate.before:
        rffi.aroundstate.before()
    return tstate

@cpython_api([PyThreadState], lltype.Void)
def PyEval_RestoreThread(space, tstate):
    """Acquire the global interpreter lock (if it has been created and thread
    support is enabled) and set the thread state to tstate, which must not be
    NULL.  If the lock has been created, the current thread must not have
    acquired it, otherwise deadlock ensues.  (This function is available even
    when thread support is disabled at compile time.)"""
    if rffi.aroundstate.after:
        rffi.aroundstate.after()
    state = space.fromcache(InterpreterState)
    state.swap_thread_state(space, tstate)

@cpython_api([], lltype.Void)
def PyEval_InitThreads(space):
    if not space.config.translation.thread:
        raise NoThreads
    from pypy.module.thread import os_thread
    os_thread.setup_threads(space)

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def PyEval_ThreadsInitialized(space):
    if not space.config.translation.thread:
        return 0
    return 1

# XXX: might be generally useful
def encapsulator(T, flavor='raw', dealloc=None):
    class MemoryCapsule(object):
        def __init__(self, space):
            self.space = space
            if space is not None:
                self.memory = lltype.malloc(T, flavor=flavor)
            else:
                self.memory = lltype.nullptr(T)
        def __del__(self):
            if self.memory:
                if dealloc and self.space:
                    dealloc(self.memory, self.space)
                lltype.free(self.memory, flavor=flavor)
    return MemoryCapsule

def ThreadState_dealloc(ts, space):
    assert space is not None
    Py_DecRef(space, ts.c_dict)
ThreadStateCapsule = encapsulator(PyThreadState.TO,
                                  dealloc=ThreadState_dealloc)

from pypy.interpreter.executioncontext import ExecutionContext

# Keep track of the ThreadStateCapsule for a particular execution context.  The
# default is for new execution contexts not to have one; it is allocated on the
# first cpyext-based request for it.
ExecutionContext.cpyext_threadstate = ThreadStateCapsule(None)

# Also keep track of whether it has been initialized yet or not (None is a valid
# PyThreadState for an execution context to have, when the GIL has been
# released, so a check against that can't be used to determine the need for
# initialization).
ExecutionContext.cpyext_initialized_threadstate = False

def cleanup_cpyext_state(self):
    self.cpyext_threadstate = None
    self.cpyext_initialized_threadstate = False
ExecutionContext.cleanup_cpyext_state = cleanup_cpyext_state

class InterpreterState(object):
    def __init__(self, space):
        self.interpreter_state = lltype.malloc(
            PyInterpreterState.TO, flavor='raw', zero=True, immortal=True)

    def new_thread_state(self, space):
        """
        Create a new ThreadStateCapsule to hold the PyThreadState for a
        particular execution context.

        :param space: A space.

        :returns: A new ThreadStateCapsule holding a newly allocated
            PyThreadState and referring to this interpreter state.
        """
        capsule = ThreadStateCapsule(space)
        ts = capsule.memory
        ts.c_interp = self.interpreter_state
        ts.c_dict = make_ref(space, space.newdict())
        return capsule


    def get_thread_state(self, space):
        """
        Get the current PyThreadState for the current execution context.

        :param space: A space.

        :returns: The current PyThreadState for the current execution context,
            or None if it does not have one.
        """
        ec = space.getexecutioncontext()
        return self._get_thread_state(space, ec).memory


    def swap_thread_state(self, space, tstate):
        """
        Replace the current thread state of the current execution context with a
        new thread state.

        :param space: The space.

        :param tstate: The new PyThreadState for the current execution context.

        :returns: The old thread state for the current execution context, either
            None or a PyThreadState.
        """
        ec = space.getexecutioncontext()
        capsule = self._get_thread_state(space, ec)
        old_tstate = capsule.memory
        capsule.memory = tstate
        return old_tstate

    def _get_thread_state(self, space, ec):
        """
        Get the ThreadStateCapsule for the given execution context, possibly
        creating a new one if it does not already have one.

        :param space: The space.
        :param ec: The ExecutionContext of which to get the thread state.
        :returns: The ThreadStateCapsule for the given execution context.
        """
        if not ec.cpyext_initialized_threadstate:
            ec.cpyext_threadstate = self.new_thread_state(space)
            ec.cpyext_initialized_threadstate = True
        return ec.cpyext_threadstate

@cpython_api([], PyThreadState, error=CANNOT_FAIL)
def PyThreadState_Get(space):
    state = space.fromcache(InterpreterState)
    return state.get_thread_state(space)

@cpython_api([], PyObject, error=CANNOT_FAIL)
def PyThreadState_GetDict(space):
    state = space.fromcache(InterpreterState)
    return state.get_thread_state(space).c_dict

@cpython_api([PyThreadState], PyThreadState, error=CANNOT_FAIL)
def PyThreadState_Swap(space, tstate):
    """Swap the current thread state with the thread state given by the argument
    tstate, which may be NULL.  The global interpreter lock must be held."""
    state = space.fromcache(InterpreterState)
    return state.swap_thread_state(space, tstate)

@cpython_api([PyThreadState], lltype.Void)
def PyEval_AcquireThread(space, tstate):
    """Acquire the global interpreter lock and set the current thread state to
    tstate, which should not be NULL.  The lock must have been created earlier.
    If this thread already has the lock, deadlock ensues.  This function is not
    available when thread support is disabled at compile time."""
    if rffi.aroundstate.after:
        # After external call is before entering Python
        rffi.aroundstate.after()

@cpython_api([PyThreadState], lltype.Void)
def PyEval_ReleaseThread(space, tstate):
    """Reset the current thread state to NULL and release the global interpreter
    lock.  The lock must have been created earlier and must be held by the current
    thread.  The tstate argument, which must not be NULL, is only used to check
    that it represents the current thread state --- if it isn't, a fatal error is
    reported. This function is not available when thread support is disabled at
    compile time."""
    if rffi.aroundstate.before:
        # Before external call is after running Python
        rffi.aroundstate.before()

PyGILState_STATE = rffi.INT

@cpython_api([], PyGILState_STATE, error=CANNOT_FAIL)
def PyGILState_Ensure(space):
    if rffi.aroundstate.after:
        # After external call is before entering Python
        rffi.aroundstate.after()
    return rffi.cast(PyGILState_STATE, 0)

@cpython_api([PyGILState_STATE], lltype.Void)
def PyGILState_Release(space, state):
    if rffi.aroundstate.before:
        # Before external call is after running Python
        rffi.aroundstate.before()

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

@cpython_api([PyInterpreterState], PyThreadState, error=CANNOT_FAIL)
def PyThreadState_New(space, interp):
    """Create a new thread state object belonging to the given interpreter
    object.  The global interpreter lock need not be held, but may be held if
    it is necessary to serialize calls to this function."""
    if not space.config.translation.thread:
        raise NoThreads
    # PyThreadState_Get will allocate a new execution context,
    # we need to protect gc and other globals with the GIL.
    rffi.aroundstate.after()
    try:
        rthread.gc_thread_start()
        return PyThreadState_Get(space)
    finally:
        rffi.aroundstate.before()

@cpython_api([PyThreadState], lltype.Void)
def PyThreadState_Clear(space, tstate):
    """Reset all information in a thread state object.  The global
    interpreter lock must be held."""
    if not space.config.translation.thread:
        raise NoThreads
    Py_DecRef(space, tstate.c_dict)
    tstate.c_dict = lltype.nullptr(PyObject.TO)
    space.threadlocals.leave_thread(space)
    space.getexecutioncontext().cleanup_cpyext_state()
    rthread.gc_thread_die()

@cpython_api([PyThreadState], lltype.Void)
def PyThreadState_Delete(space, tstate):
    """Destroy a thread state object.  The global interpreter lock need not
    be held.  The thread state must have been reset with a previous call to
    PyThreadState_Clear()."""

@cpython_api([], lltype.Void)
def PyThreadState_DeleteCurrent(space):
    """Destroy a thread state object.  The global interpreter lock need not
    be held.  The thread state must have been reset with a previous call to
    PyThreadState_Clear()."""

