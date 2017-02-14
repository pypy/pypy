from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, CONST_STRING, FILEP)
from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.object import Py_PRINT_RAW
from pypy.interpreter.error import OperationError, oefmt

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
        w_readline = space.getattr(w_obj, space.newtext('readline'))
    except OperationError:
        raise oefmt(space.w_TypeError,
            "argument must be a file, or have a readline() method.")

    n = rffi.cast(lltype.Signed, n)
    if space.is_true(space.gt(space.newint(n), space.newint(0))):
        return space.call_function(w_readline, space.newint(n))
    elif space.is_true(space.lt(space.newint(n), space.newint(0))):
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
    w_filename = space.newbytes(rffi.charp2str(filename))
    w_mode = space.newtext(rffi.charp2str(mode))
    return space.call_method(space.builtin, 'open', w_filename, w_mode)

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
    w_str = space.newtext(rffi.charp2str(s))
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
    w_name = space.getattr(w_p, space.newtext("name"))
    return w_name     # borrowed ref, should be a W_StringObject from the file
