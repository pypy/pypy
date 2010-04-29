from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, PyObject, CANNOT_FAIL, CONST_STRING)

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyEval_CallObjectWithKeywords(space, w_obj, w_arg, w_kwds):
    return space.call(w_obj, w_arg, w_kwds)

@cpython_api([PyObject, PyObject], PyObject)
def PyObject_CallObject(space, w_obj, w_arg):
    """
    Call a callable Python object callable_object, with arguments given by the
    tuple args.  If no arguments are needed, then args may be NULL.  Returns
    the result of the call on success, or NULL on failure.  This is the equivalent
    of the Python expression apply(callable_object, args) or
    callable_object(*args)."""
    return space.call(w_obj, w_arg)

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyObject_Call(space, w_obj, w_args, w_kw):
    """
    Call a callable Python object, with arguments given by the
    tuple args, and named arguments given by the dictionary kw. If no named
    arguments are needed, kw may be NULL. args must not be NULL, use an
    empty tuple if no arguments are needed. Returns the result of the call on
    success, or NULL on failure.  This is the equivalent of the Python expression
    apply(callable_object, args, kw) or callable_object(*args, **kw)."""
    return space.call(w_obj, w_args, w_kw)

# These constants are also defined in include/eval.h
Py_single_input = 256
Py_file_input = 257
Py_eval_input = 258

@cpython_api([CONST_STRING, rffi.INT_real, PyObject, PyObject], PyObject)
def PyRun_String(space, str, start, w_globals, w_locals):
    """This is a simplified interface to PyRun_StringFlags() below, leaving
    flags set to NULL."""
    from pypy.module.__builtin__ import compiling
    w_source = space.wrap(rffi.charp2str(str))
    filename = "<string>"
    start = rffi.cast(lltype.Signed, start)
    if start == Py_file_input:
        mode = 'exec'
    elif start == Py_eval_input:
        mode = 'eval'
    elif start == Py_single_input:
        mode = 'single'
    else:
        raise OperationError(space.w_ValueError, space.wrap(
            "invalid mode parameter for PyRun_String"))
    w_code = compiling.compile(space, w_source, filename, mode)
    return compiling.eval(space, w_code, w_globals, w_locals)

