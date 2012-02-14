from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, CONST_STRING, FILEP, build_type_checkers)
from pypy.module.cpyext.pyobject import PyObject, borrow_from
from pypy.module.cpyext.object import Py_PRINT_RAW
from pypy.interpreter.error import OperationError
from pypy.module._file.interp_file import W_File

PyFile_Check, PyFile_CheckExact = build_type_checkers("File", W_File)

@cpython_api([PyObject, rffi.INT_real], PyObject)
def PyFile_GetLine(space, w_obj, n):
    """
    Equivalent to p.readline([n]), this function reads one line from the
    object p.  p may be a file object or any object with a readline()
    method.  If n is 0, exactly one line is read, regardless of the length of
    the line.  If n is greater than 0, no more than n bytes will be read
    from the file; a partial line can be returned.  In both cases, an empty string
    is returned if the end of the file is reached immediately.  If n is less than
    0, however, one line is read regardless of length, but EOFError is
    raised if the end of the file is reached immediately."""
    try:
        w_readline = space.getattr(w_obj, space.wrap('readline'))
    except OperationError:
        raise OperationError(
            space.w_TypeError, space.wrap(
            "argument must be a file, or have a readline() method."))

    n = rffi.cast(lltype.Signed, n)
    if space.is_true(space.gt(space.wrap(n), space.wrap(0))):
        return space.call_function(w_readline, space.wrap(n))
    elif space.is_true(space.lt(space.wrap(n), space.wrap(0))):
        return space.call_function(w_readline)
    else:
        # XXX Raise EOFError as specified
        return space.call_function(w_readline)

@cpython_api([CONST_STRING, CONST_STRING], PyObject)
def PyFile_FromString(space, filename, mode):
    """
    On success, return a new file object that is opened on the file given by
    filename, with a file mode given by mode, where mode has the same
    semantics as the standard C routine fopen().  On failure, return NULL."""
    w_filename = space.wrap(rffi.charp2str(filename))
    w_mode = space.wrap(rffi.charp2str(mode))
    return space.call_method(space.builtin, 'file', w_filename, w_mode)

@cpython_api([FILEP, CONST_STRING, CONST_STRING, rffi.VOIDP], PyObject)
def PyFile_FromFile(space, fp, name, mode, close):
    """Create a new PyFileObject from the already-open standard C file
    pointer, fp.  The function close will be called when the file should be
    closed.  Return NULL on failure."""
    raise NotImplementedError

@cpython_api([PyObject, rffi.INT_real], lltype.Void)
def PyFile_SetBufSize(space, w_file, n):
    """Available on systems with setvbuf() only.  This should only be called
    immediately after file object creation."""
    raise NotImplementedError

@cpython_api([CONST_STRING, PyObject], rffi.INT_real, error=-1)
def PyFile_WriteString(space, s, w_p):
    """Write string s to file object p.  Return 0 on success or -1 on
    failure; the appropriate exception will be set."""
    w_str = space.wrap(rffi.charp2str(s))
    space.call_method(w_p, "write", w_str)
    return 0

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real, error=-1)
def PyFile_WriteObject(space, w_obj, w_p, flags):
    """
    Write object obj to file object p.  The only supported flag for flags is
    Py_PRINT_RAW; if given, the str() of the object is written
    instead of the repr().  Return 0 on success or -1 on failure; the
    appropriate exception will be set."""
    if rffi.cast(lltype.Signed, flags) & Py_PRINT_RAW:
        w_str = space.str(w_obj)
    else:
        w_str = space.repr(w_obj)
    space.call_method(w_p, "write", w_str)
    return 0

@cpython_api([PyObject], PyObject)
def PyFile_Name(space, w_p):
    """Return the name of the file specified by p as a string object."""
    return borrow_from(w_p, space.getattr(w_p, space.wrap("name")))

@cpython_api([PyObject, rffi.INT_real], rffi.INT_real, error=CANNOT_FAIL)
def PyFile_SoftSpace(space, w_p, newflag):
    """
    This function exists for internal use by the interpreter.  Set the
    softspace attribute of p to newflag and return the previous value.
    p does not have to be a file object for this function to work
    properly; any object is supported (thought its only interesting if
    the softspace attribute can be set).  This function clears any
    errors, and will return 0 as the previous value if the attribute
    either does not exist or if there were errors in retrieving it.
    There is no way to detect errors from this function, but doing so
    should not be needed."""
    try:
        if newflag:
            w_newflag = space.w_True
        else:
            w_newflag = space.w_False
        oldflag = space.int_w(space.getattr(w_p, space.wrap("softspace")))
        space.setattr(w_p, space.wrap("softspace"), w_newflag)
        return oldflag
    except OperationError, e:
        return 0

