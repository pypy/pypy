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

pending_call = lltype.Ptr(lltype.FuncType([rffi.VOIDP], rffi.INT_real))
@cpython_api([pending_call, rffi.VOIDP], rffi.INT_real, error=-1)
def Py_AddPendingCall(space, func, arg):
    """Post a notification to the Python main thread.  If successful,
    func will be called with the argument arg at the earliest
    convenience.  func will be called having the global interpreter
    lock held and can thus use the full Python API and can take any
    action such as setting object attributes to signal IO completion.
    It must return 0 on success, or -1 signalling an exception.  The
    notification function won't be interrupted to perform another
    asynchronous notification recursively, but it can still be
    interrupted to switch threads if the global interpreter lock is
    released, for example, if it calls back into Python code.

    This function returns 0 on success in which case the notification
    has been scheduled.  Otherwise, for example if the notification
    buffer is full, it returns -1 without setting any exception.

    This function can be called on any thread, be it a Python thread
    or some other system thread.  If it is a Python thread, it doesn't
    matter if it holds the global interpreter lock or not.
    """
    return -1

thread_func = lltype.Ptr(lltype.FuncType([rffi.VOIDP], lltype.Void))
@cpython_api([thread_func, rffi.VOIDP], rffi.INT_real, error=-1)
def PyThread_start_new_thread(space, func, arg):
    return -1
