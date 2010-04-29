from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.api import cpython_api, Py_ssize_t, CANNOT_FAIL, CConfig
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.pystate import PyThreadState, PyInterpreterState


@cpython_api([PyObject], rffi.VOIDP, error=CANNOT_FAIL) #XXX
def PyFile_AsFile(space, p):
    """Return the file object associated with p as a FILE*.
    
    If the caller will ever use the returned FILE* object while
    the GIL is released it must also call the PyFile_IncUseCount() and
    PyFile_DecUseCount() functions described below as appropriate."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyObject_GetIter(space, o):
    """This is equivalent to the Python expression iter(o). It returns a new
    iterator for the object argument, or the object  itself if the object is already
    an iterator.  Raises TypeError and returns NULL if the object cannot be
    iterated."""
    raise NotImplementedError

@cpython_api([PyObject], PyObject)
def PyIter_Next(space, o):
    """Return the next value from the iteration o.  If the object is an iterator,
    this retrieves the next value from the iteration, and returns NULL with no
    exception set if there are no remaining items.  If the object is not an
    iterator, TypeError is raised, or if there is an error in retrieving the
    item, returns NULL and passes along the exception."""
    raise NotImplementedError

@cpython_api([rffi.ULONG], PyObject)
def PyLong_FromUnsignedLong(space, v):
    """Return a new PyLongObject object from a C unsigned long, or
    NULL on failure."""
    raise NotImplementedError

FILE = rffi.VOIDP_real.TO
FILEP = lltype.Ptr(FILE)
@cpython_api([PyObject, FILEP, rffi.INT_real], rffi.INT_real, error=-1)
def PyObject_Print(space, o, fp, flags):
    """Print an object o, on file fp.  Returns -1 on error.  The flags argument
    is used to enable certain printing options.  The only option currently supported
    is Py_PRINT_RAW; if given, the str() of the object is written
    instead of the repr()."""
    raise NotImplementedError

@cpython_api([], lltype.Void)
def PyErr_Print(space):
    """Alias for PyErr_PrintEx(1)."""
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

