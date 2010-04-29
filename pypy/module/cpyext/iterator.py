from pypy.module.cpyext.api import generic_cpy_call, cpython_api, PyObject
from pypy.interpreter.error import OperationError
import pypy.module.__builtin__.operation as operation


@cpython_api([PyObject, PyObject], PyObject)
def PyCallIter_New(space, w_callable, w_sentinel):
    """Return a new iterator.  The first parameter, callable, can be any Python
    callable object that can be called with no parameters; each call to it should
    return the next item in the iteration.  When callable returns a value equal to
    sentinel, the iteration will be terminated.
    """
    return operation.iter_sentinel(space, w_callable, w_sentinel)

