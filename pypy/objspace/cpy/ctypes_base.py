"""
CTypes base classes to support the particularities of the CPyObjSpace
when it uses the CPython API: the W_Object class and the cpyapi accessor.
"""

import sys
from ctypes import *
from pypy.rpython.rctypes import apyobject
from pypy.interpreter.error import OperationError
from pypy.tool.sourcetools import func_with_new_name


class W_Object(py_object):
    """A py_object subclass, representing wrapped objects for the CPyObjSpace.
    The reason we don't use py_object directly is that if py_object is
    specified as the restype of a function, the function call unwraps it
    automatically.  With W_Object, however, the function call returns a
    W_Object instance.
    """
    def __repr__(self):
        return 'W_Object(%r)' % (self.value,)

apyobject.register_py_object_subclass(W_Object)


class LevelError(Exception):
    pass

class CPyAPI(PyDLL):
    """Class of the singleton 'cpyapi' object, out of which C functions
    are getattr'd.  It returns C function whose exception behavior matches
    the one required for the CPyObjSpace: exceptions are wrapped in
    OperationErrors.
    """
    class _FuncPtr(PyDLL._FuncPtr):
        _flags_ = PyDLL._FuncPtr._flags_

        def __call__(*args, **kwds):
            try:
                return PyDLL._FuncPtr.__call__(*args, **kwds)
            except OperationError, e:
                raise LevelError, "unexpected OperationError: %r" % (e,)
            except:
                exc, val, tb = sys.exc_info()
                raise OperationError(W_Object(exc),
                                     W_Object(val),
                                     W_Object(tb))

cpyapi = CPyAPI.__new__(CPyAPI)
cpyapi.__dict__ = pythonapi.__dict__.copy()
