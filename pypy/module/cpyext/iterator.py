from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import (generic_cpy_call, cpython_api, PyObject,
    CANNOT_FAIL)
import pypy.module.__builtin__.operation as operation
from pypy.rpython.lltypesystem import rffi


@cpython_api([PyObject, PyObject], PyObject)
def PyCallIter_New(space, w_callable, w_sentinel):
    """Return a new iterator.  The first parameter, callable, can be any Python
    callable object that can be called with no parameters; each call to it should
    return the next item in the iteration.  When callable returns a value equal to
    sentinel, the iteration will be terminated.
    """
    return operation.iter_sentinel(space, w_callable, w_sentinel)

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyIter_Check(space, w_obj):
    """Return true if the object o supports the iterator protocol."""
    try:
        w_attr = space.getattr(space.type(w_obj), space.wrap("next"))
    except:
        return False
    else:
        return space.is_true(space.callable(w_attr))
