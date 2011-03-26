import os

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL, CONST_STRING
from pypy.module.exceptions.interp_exceptions import W_RuntimeWarning
from pypy.module.cpyext.pyobject import (
    PyObject, PyObjectP, make_ref, from_ref, Py_DecRef, borrow_from)
from pypy.module.cpyext.state import State
from pypy.module.cpyext.import_ import PyImport_Import
from pypy.rlib.rposix import get_errno

@cpython_api([PyObject, PyObject], lltype.Void)
def PyErr_SetObject(space, w_type, w_value):
    """This function is similar to PyErr_SetString() but lets you specify an
    arbitrary Python object for the "value" of the exception."""
    state = space.fromcache(State)
    state.set_exception(OperationError(w_type, w_value))

@cpython_api([PyObject, CONST_STRING], lltype.Void)
def PyErr_SetString(space, w_type, message_ptr):
    message = rffi.charp2str(message_ptr)
    PyErr_SetObject(space, w_type, space.wrap(message))

@cpython_api([PyObject], lltype.Void, error=CANNOT_FAIL)
def PyErr_SetNone(space, w_type):
    """This is a shorthand for PyErr_SetObject(type, Py_None)."""
    PyErr_SetObject(space, w_type, space.w_None)

@cpython_api([], PyObject)
def PyErr_Occurred(space):
    state = space.fromcache(State)
    if state.operror is None:
        return None
    return borrow_from(None, state.operror.w_type)

@cpython_api([], lltype.Void)
def PyErr_Clear(space):
    state = space.fromcache(State)
    state.clear_exception()

@cpython_api([PyObject], PyObject)
def PyExceptionInstance_Class(space, w_obj):
    return space.type(w_obj)

@cpython_api([PyObjectP, PyObjectP, PyObjectP], lltype.Void)
def PyErr_Fetch(space, ptype, pvalue, ptraceback):
    """Retrieve the error indicator into three variables whose addresses are passed.
    If the error indicator is not set, set all three variables to NULL.  If it is
    set, it will be cleared and you own a reference to each object retrieved.  The
    value and traceback object may be NULL even when the type object is not.

    This function is normally only used by code that needs to handle exceptions or
    by code that needs to save and restore the error indicator temporarily."""
    state = space.fromcache(State)
    operror = state.clear_exception()
    if operror:
        ptype[0] = make_ref(space, operror.w_type)
        pvalue[0] = make_ref(space, operror.get_w_value(space))
        ptraceback[0] = make_ref(space, space.wrap(operror.application_traceback))
    else:
        ptype[0] = lltype.nullptr(PyObject.TO)
        pvalue[0] = lltype.nullptr(PyObject.TO)
        ptraceback[0] = lltype.nullptr(PyObject.TO)

@cpython_api([PyObject, PyObject, PyObject], lltype.Void)
def PyErr_Restore(space, w_type, w_value, w_traceback):
    """Set  the error indicator from the three objects.  If the error indicator is
    already set, it is cleared first.  If the objects are NULL, the error
    indicator is cleared.  Do not pass a NULL type and non-NULL value or
    traceback.  The exception type should be a class.  Do not pass an invalid
    exception type or value. (Violating these rules will cause subtle problems
    later.)  This call takes away a reference to each object: you must own a
    reference to each object before the call and after the call you no longer own
    these references.  (If you don't understand this, don't use this function.  I
    warned you.)

    This function is normally only used by code that needs to save and restore the
    error indicator temporarily; use PyErr_Fetch() to save the current
    exception state."""
    state = space.fromcache(State)
    if w_type is None:
        state.clear_exception()
        return
    state.set_exception(OperationError(w_type, w_value))
    Py_DecRef(space, w_type)
    Py_DecRef(space, w_value)
    Py_DecRef(space, w_traceback)

@cpython_api([PyObjectP, PyObjectP, PyObjectP], lltype.Void)
def PyErr_NormalizeException(space, exc_p, val_p, tb_p):
    """Under certain circumstances, the values returned by PyErr_Fetch() below
    can be "unnormalized", meaning that *exc is a class object but *val is
    not an instance of the  same class.  This function can be used to instantiate
    the class in that case.  If the values are already normalized, nothing happens.
    The delayed normalization is implemented to improve performance."""
    operr = OperationError(from_ref(space, exc_p[0]),
                           from_ref(space, val_p[0]))
    operr.normalize_exception(space)
    Py_DecRef(space, exc_p[0])
    Py_DecRef(space, val_p[0])
    exc_p[0] = make_ref(space, operr.w_type)
    val_p[0] = make_ref(space, operr.get_w_value(space))

@cpython_api([], lltype.Void)
def PyErr_BadArgument(space):
    """This is a shorthand for PyErr_SetString(PyExc_TypeError, message), where
    message indicates that a built-in operation was invoked with an illegal
    argument.  It is mostly for internal use."""
    raise OperationError(space.w_TypeError,
            space.wrap("bad argument type for built-in operation"))

@cpython_api([], lltype.Void)
def PyErr_BadInternalCall(space):
    raise OperationError(space.w_SystemError, space.wrap("Bad internal call!"))

@cpython_api([], PyObject, error=CANNOT_FAIL)
def PyErr_NoMemory(space):
    """This is a shorthand for PyErr_SetNone(PyExc_MemoryError); it returns NULL
    so an object allocation function can write return PyErr_NoMemory(); when it
    runs out of memory.
    Return value: always NULL."""
    PyErr_SetNone(space, space.w_MemoryError)

@cpython_api([PyObject], PyObject)
def PyErr_SetFromErrno(space, w_type):
    """
    This is a convenience function to raise an exception when a C library function
    has returned an error and set the C variable errno.  It constructs a
    tuple object whose first item is the integer errno value and whose
    second item is the corresponding error message (gotten from strerror()),
    and then calls PyErr_SetObject(type, object).  On Unix, when the
    errno value is EINTR, indicating an interrupted system call,
    this calls PyErr_CheckSignals(), and if that set the error indicator,
    leaves it set to that.  The function always returns NULL, so a wrapper
    function around a system call can write return PyErr_SetFromErrno(type);
    when the system call returns an error.
    Return value: always NULL."""
    PyErr_SetFromErrnoWithFilename(space, w_type,
                                   lltype.nullptr(rffi.CCHARP.TO))

@cpython_api([PyObject, rffi.CCHARP], PyObject)
def PyErr_SetFromErrnoWithFilename(space, w_type, llfilename):
    """Similar to PyErr_SetFromErrno(), with the additional behavior that if
    filename is not NULL, it is passed to the constructor of type as a third
    parameter.  In the case of exceptions such as IOError and OSError,
    this is used to define the filename attribute of the exception instance.
    Return value: always NULL."""
    # XXX Doesn't actually do anything with PyErr_CheckSignals.
    errno = get_errno()
    msg = os.strerror(errno)
    if llfilename:
        w_filename = rffi.charp2str(llfilename)
        w_error = space.call_function(w_type,
                                      space.wrap(errno),
                                      space.wrap(msg),
                                      space.wrap(w_filename))
    else:
        w_error = space.call_function(w_type,
                                      space.wrap(errno),
                                      space.wrap(msg))
    raise OperationError(w_type, w_error)

@cpython_api([], rffi.INT_real, error=-1)
def PyErr_CheckSignals(space):
    """
    This function interacts with Python's signal handling.  It checks whether a
    signal has been sent to the processes and if so, invokes the corresponding
    signal handler.  If the signal module is supported, this can invoke a
    signal handler written in Python.  In all cases, the default effect for
    SIGINT is to raise the  KeyboardInterrupt exception.  If an
    exception is raised the error indicator is set and the function returns -1;
    otherwise the function returns 0.  The error indicator may or may not be
    cleared if it was previously set."""
    # XXX implement me
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyErr_GivenExceptionMatches(space, w_given, w_exc):
    """Return true if the given exception matches the exception in exc.  If
    exc is a class object, this also returns true when given is an instance
    of a subclass.  If exc is a tuple, all exceptions in the tuple (and
    recursively in subtuples) are searched for a match."""
    if (space.is_true(space.isinstance(w_given, space.w_BaseException)) or
        space.is_oldstyle_instance(w_given)):
        w_given_type = space.exception_getclass(w_given)
    else:
        w_given_type = w_given
    return space.exception_match(w_given_type, w_exc)

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyErr_ExceptionMatches(space, w_exc):
    """Equivalent to PyErr_GivenExceptionMatches(PyErr_Occurred(), exc).  This
    should only be called when an exception is actually set; a memory access
    violation will occur if no exception has been raised."""
    w_type = PyErr_Occurred(space)
    return PyErr_GivenExceptionMatches(space, w_type, w_exc)


@cpython_api([PyObject, CONST_STRING, rffi.INT_real], rffi.INT_real, error=-1)
def PyErr_WarnEx(space, w_category, message_ptr, stacklevel):
    """Issue a warning message.  The category argument is a warning category (see
    below) or NULL; the message argument is a message string.  stacklevel is a
    positive number giving a number of stack frames; the warning will be issued from
    the  currently executing line of code in that stack frame.  A stacklevel of 1
    is the function calling PyErr_WarnEx(), 2 is  the function above that,
    and so forth.

    This function normally prints a warning message to sys.stderr; however, it is
    also possible that the user has specified that warnings are to be turned into
    errors, and in that case this will raise an exception.  It is also possible that
    the function raises an exception because of a problem with the warning machinery
    (the implementation imports the warnings module to do the heavy lifting).
    The return value is 0 if no exception is raised, or -1 if an exception
    is raised.  (It is not possible to determine whether a warning message is
    actually printed, nor what the reason is for the exception; this is
    intentional.)  If an exception is raised, the caller should do its normal
    exception handling (for example, Py_DECREF() owned references and return
    an error value).

    Warning categories must be subclasses of Warning; the default warning
    category is RuntimeWarning.  The standard Python warning categories are
    available as global variables whose names are PyExc_ followed by the Python
    exception name. These have the type PyObject*; they are all class
    objects. Their names are PyExc_Warning, PyExc_UserWarning,
    PyExc_UnicodeWarning, PyExc_DeprecationWarning,
    PyExc_SyntaxWarning, PyExc_RuntimeWarning, and
    PyExc_FutureWarning.  PyExc_Warning is a subclass of
    PyExc_Exception; the other warning categories are subclasses of
    PyExc_Warning.

    For information about warning control, see the documentation for the
    warnings module and the -W option in the command line
    documentation.  There is no C API for warning control."""
    if w_category is None:
        w_category = space.w_None
    w_message = space.wrap(rffi.charp2str(message_ptr))
    w_stacklevel = space.wrap(rffi.cast(lltype.Signed, stacklevel))

    w_module = PyImport_Import(space, space.wrap("warnings"))
    w_warn = space.getattr(w_module, space.wrap("warn"))
    space.call_function(w_warn, w_message, w_category, w_stacklevel)
    return 0

@cpython_api([PyObject, CONST_STRING], rffi.INT_real, error=-1)
def PyErr_Warn(space, w_category, message):
    """Issue a warning message.  The category argument is a warning category (see
    below) or NULL; the message argument is a message string.  The warning will
    appear to be issued from the function calling PyErr_Warn(), equivalent to
    calling PyErr_WarnEx() with a stacklevel of 1.

    Deprecated; use PyErr_WarnEx() instead."""
    return PyErr_WarnEx(space, w_category, message, 1)

@cpython_api([rffi.INT_real], lltype.Void)
def PyErr_PrintEx(space, set_sys_last_vars):
    """Print a standard traceback to sys.stderr and clear the error indicator.
    Call this function only when the error indicator is set.  (Otherwise it will
    cause a fatal error!)

    If set_sys_last_vars is nonzero, the variables sys.last_type,
    sys.last_value and sys.last_traceback will be set to the
    type, value and traceback of the printed exception, respectively."""
    if not PyErr_Occurred(space):
        PyErr_BadInternalCall(space)
    state = space.fromcache(State)
    operror = state.clear_exception()

    w_type = operror.w_type
    w_value = operror.get_w_value(space)
    w_tb = space.wrap(operror.application_traceback)

    if rffi.cast(lltype.Signed, set_sys_last_vars):
        space.sys.setdictvalue(space, "last_type", w_type)
        space.sys.setdictvalue(space, "last_value", w_value)
        space.sys.setdictvalue(space, "last_traceback", w_tb)

    space.call_function(space.sys.get("excepthook"),
                        w_type, w_value, w_tb)

@cpython_api([], lltype.Void)
def PyErr_Print(space):
    """Alias for PyErr_PrintEx(1)."""
    PyErr_PrintEx(space, 1)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyTraceBack_Print(space, w_tb, w_file):
    space.call_method(w_file, "write", space.wrap(
        'Traceback (most recent call last):\n'))
    w_traceback = space.call_method(space.builtin, '__import__',
                                    space.wrap("traceback"))
    space.call_method(w_traceback, "print_tb", w_tb, space.w_None, w_file)
    return 0

@cpython_api([PyObject], lltype.Void)
def PyErr_WriteUnraisable(space, w_where):
    """This utility function prints a warning message to sys.stderr when an
    exception has been set but it is impossible for the interpreter to actually
    raise the exception.  It is used, for example, when an exception occurs in
    an __del__() method.

    The function is called with a single argument obj that identifies the
    context in which the unraisable exception occurred. The repr of obj will be
    printed in the warning message."""

    state = space.fromcache(State)
    operror = state.clear_exception()
    if operror:
        operror.write_unraisable(space, space.str_w(space.repr(w_where)))

@cpython_api([], lltype.Void)
def PyErr_SetInterrupt(space):
    """This function simulates the effect of a SIGINT signal arriving --- the
    next time PyErr_CheckSignals() is called, KeyboardInterrupt will be raised.
    It may be called without holding the interpreter lock."""
    space.check_signal_action.set_interrupt()

