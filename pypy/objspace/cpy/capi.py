import sys
from ctypes import *
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes import apyobject

class W_Object(py_object):
    "A py_object subclass, representing wrapped objects for the CPyObjSpace."
    def __repr__(self):
        return 'W_Object(%r)' % (self.value,)

apyobject.register_py_object_subclass(W_Object)


###############################################################
# ____________________ Types and constants ____________________

##Py_ssize_t = ctypes_platform.getsimpletype('Py_ssize_t',
##    """ #include <Python.h>
##        #if PY_VERSION_HEX < 0x02050000   /* < 2.5 */
##        typedef int Py_ssize_t;
##        #endif
##    """,                                   c_int)

##Py_LT = ctypes_platform.getconstantinteger('Py_LT', "#include <Python.h>")
##Py_LE = ctypes_platform.getconstantinteger('Py_LE', "#include <Python.h>")
##Py_EQ = ctypes_platform.getconstantinteger('Py_EQ', "#include <Python.h>")
##Py_NE = ctypes_platform.getconstantinteger('Py_NE', "#include <Python.h>")
##Py_GT = ctypes_platform.getconstantinteger('Py_GT', "#include <Python.h>")
##Py_GE = ctypes_platform.getconstantinteger('Py_GE', "#include <Python.h>")

# XXX ctypes_platform needs to be enhanced...
Py_ssize_t = c_int
Py_LT, Py_LE, Py_EQ, Py_NE, Py_GT, Py_GE = range(6)


###########################################################
# ____________________ Object Protocol ____________________

PyObject_GetAttr = pythonapi.PyObject_GetAttr
PyObject_GetAttr.argtypes = [W_Object, W_Object]
PyObject_GetAttr.restype = W_Object

PyObject_GetItem = pythonapi.PyObject_GetItem
PyObject_GetItem.argtypes = [W_Object, W_Object]
PyObject_GetItem.restype = W_Object

PyObject_SetItem = pythonapi.PyObject_SetItem
PyObject_SetItem.argtypes = [W_Object, W_Object, W_Object]
PyObject_SetItem.restype = c_int

PyObject_Call = pythonapi.PyObject_Call
PyObject_Call.argtypes = [W_Object, W_Object, W_Object]
PyObject_Call.restype = W_Object

PyObject_RichCompare = pythonapi.PyObject_RichCompare
PyObject_RichCompare.argtypes = [W_Object, W_Object, c_int]
PyObject_RichCompare.restype = W_Object

PyObject_RichCompareBool = pythonapi.PyObject_RichCompareBool
PyObject_RichCompareBool.argtypes = [W_Object, W_Object, c_int]
PyObject_RichCompareBool.restype = c_int


#############################################################
# ____________________ Sequence Protocol ____________________

PySequence_Tuple = pythonapi.PySequence_Tuple
PySequence_Tuple.argtypes = [W_Object]
PySequence_Tuple.restype = W_Object

PySequence_SetItem = pythonapi.PySequence_SetItem
PySequence_SetItem.argtypes = [W_Object, Py_ssize_t, W_Object]
PySequence_SetItem.restype = c_int


###########################################################
# ____________________ Numeric Objects ____________________

PyInt_FromLong = pythonapi.PyInt_FromLong
PyInt_FromLong.argtypes = [c_long]
PyInt_FromLong.restype = W_Object


###################################################
# ____________________ Strings ____________________

PyString_FromStringAndSize = pythonapi.PyString_FromStringAndSize
PyString_FromStringAndSize.argtypes = [c_char_p, Py_ssize_t]
PyString_FromStringAndSize.restype = W_Object

PyString_InternInPlace = pythonapi.PyString_InternInPlace
PyString_InternInPlace.argtypes = [POINTER(W_Object)]
PyString_InternInPlace.restype = None


##################################################
# ____________________ Tuples ____________________

PyTuple_New = pythonapi.PyTuple_New
PyTuple_New.argtypes = [Py_ssize_t]
PyTuple_New.restype = W_Object


#################################################
# ____________________ Lists ____________________

PyList_New = pythonapi.PyList_New
PyList_New.argtypes = [Py_ssize_t]
PyList_New.restype = W_Object

PyList_Append = pythonapi.PyList_Append
PyList_Append.argtypes = [W_Object, W_Object]
PyList_Append.restype = c_int


########################################################
# ____________________ Dictionaries ____________________

PyDict_New = pythonapi.PyDict_New
PyDict_New.argtypes = []
PyDict_New.restype = W_Object

PyDict_SetItem = pythonapi.PyDict_SetItem
PyDict_SetItem.argtypes = [W_Object, W_Object, W_Object]
PyDict_SetItem.restype = c_int


#####################################################
# ____________________ Utilities ____________________

PyImport_ImportModule = pythonapi.PyImport_ImportModule
PyImport_ImportModule.argtypes = [c_char_p]
PyImport_ImportModule.restype = W_Object
