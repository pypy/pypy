from pypy.module._demo import demo

from ctypes import *

Py_ssize_t = c_int    # XXX changes in Python 2.5

PyObject_GetAttr = pythonapi.PyObject_GetAttr
PyObject_GetAttr.argtypes = [py_object, py_object]
PyObject_GetAttr.restype = py_object

PyImport_ImportModule = pythonapi.PyImport_ImportModule
PyImport_ImportModule.argtypes = [c_char_p]
PyImport_ImportModule.restype = py_object

PyInt_FromLong = pythonapi.PyInt_FromLong
PyInt_FromLong.argtypes = [c_long]
PyInt_FromLong.restype = py_object

PyString_FromStringAndSize = pythonapi.PyString_FromStringAndSize
PyString_FromStringAndSize.argtypes = [c_char_p, Py_ssize_t]
PyString_FromStringAndSize.restype = py_object

PyObject_Call = pythonapi.PyObject_Call
PyObject_Call.argtypes = [py_object, py_object, py_object]
PyObject_Call.restype = py_object

PyTuple_New = pythonapi.PyTuple_New
PyTuple_New.argtypes = [Py_ssize_t]
PyTuple_New.restype = py_object

PyDict_New = pythonapi.PyDict_New
PyDict_New.argtypes = []
PyDict_New.restype = py_object


class CPyObjSpace:

    def __init__(self):
        self.w_int = py_object(int)
        self.w_None = py_object(None)

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

    def getattr(self, w_obj, w_attr):
        return PyObject_GetAttr(w_obj, w_attr)

    def call_function(self, w_callable):
        return PyObject_Call(w_callable, PyTuple_New(0), PyDict_New())


space = CPyObjSpace()

def entry_point(n):
    return demo.measuretime(space, n, space.w_int)

# _____ Define and setup target ___

def target(*args):
    return entry_point, [int]


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        N = 500000
    else:
        N = int(sys.argv[1])
    print 'Timing for %d iterations...' % N
    print entry_point(N), 'seconds'
