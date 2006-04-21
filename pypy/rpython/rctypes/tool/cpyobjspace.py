import sys
from ctypes import *

class W_Object(py_object):
    "A py_object subclass, representing wrapped objects for the CPyObjSpace."

from pypy.rpython.rctypes import apyobject
apyobject.register_py_object_subclass(W_Object)


assert sys.version < (2, 5), "XXX fix Py_ssize_t for Python 2.5"
Py_ssize_t = c_int

PyObject_GetAttr = pythonapi.PyObject_GetAttr
PyObject_GetAttr.argtypes = [W_Object, W_Object]
PyObject_GetAttr.restype = W_Object

PyImport_ImportModule = pythonapi.PyImport_ImportModule
PyImport_ImportModule.argtypes = [c_char_p]
PyImport_ImportModule.restype = W_Object

PyInt_FromLong = pythonapi.PyInt_FromLong
PyInt_FromLong.argtypes = [c_long]
PyInt_FromLong.restype = W_Object

PyString_FromStringAndSize = pythonapi.PyString_FromStringAndSize
PyString_FromStringAndSize.argtypes = [c_char_p, Py_ssize_t]
PyString_FromStringAndSize.restype = W_Object

PyString_InternInPlace = pythonapi.PyString_InternInPlace
PyString_InternInPlace.argtypes = [POINTER(W_Object)]
PyString_InternInPlace.restype = None

PyObject_SetItem = pythonapi.PyObject_SetItem
PyObject_SetItem.argtypes = [W_Object, W_Object, W_Object]
PyObject_SetItem.restype = c_int

PyObject_Call = pythonapi.PyObject_Call
PyObject_Call.argtypes = [W_Object, W_Object, W_Object]
PyObject_Call.restype = W_Object

PyTuple_New = pythonapi.PyTuple_New
PyTuple_New.argtypes = [Py_ssize_t]
PyTuple_New.restype = W_Object

PyDict_New = pythonapi.PyDict_New
PyDict_New.argtypes = []
PyDict_New.restype = W_Object

PyDict_SetItem = pythonapi.PyDict_SetItem
PyDict_SetItem.argtypes = [W_Object, W_Object, W_Object]
PyDict_SetItem.restype = c_int


class CPyObjSpace:
    W_Object = W_Object

    def __init__(self):
        self.w_int   = W_Object(int)
        self.w_None  = W_Object(None)
        self.w_False = W_Object(False)
        self.w_True  = W_Object(True)

    def getbuiltinmodule(self, name):
        return PyImport_ImportModule(name)

    def wrap(self, x):
        if x is None:
            return self.w_None
        if isinstance(x, int):
            return PyInt_FromLong(x)
        if isinstance(x, str):
            return PyString_FromStringAndSize(x, len(x))
        raise TypeError("wrap(%r)" % (x,))
    wrap._annspecialcase_ = "specialize:wrap"

    getattr = staticmethod(PyObject_GetAttr)

    def call_function(self, w_callable):
        return PyObject_Call(w_callable, PyTuple_New(0), PyDict_New())

    def _freeze_(self):
        return True

    def new_interned_str(self, s):
        w_s = self.wrap(s)
        PyString_InternInPlace(byref(w_s))
        return w_s

    def newdict(self, items_w):
        w_dict = PyDict_New()
        for w_key, w_value in items_w:
            PyDict_SetItem(w_dict, w_key, w_value)
        return w_dict
