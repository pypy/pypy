"""
CTypes declarations for the CPython API.
"""
import sys
import ctypes
from ctypes import *
from pypy.rpython.rctypes.tool import ctypes_platform
##from pypy.rpython.rctypes.implementation import CALLBACK_FUNCTYPE
from pypy.objspace.cpy.ctypes_base import W_Object, cpyapi


###############################################################
# ____________________ Types and constants ____________________

##PyCFunction = CALLBACK_FUNCTYPE(W_Object, W_Object, W_Object, callconv=PyDLL)
##PyNoArgsFunction = CALLBACK_FUNCTYPE(W_Object, W_Object, callconv=PyDLL)
##PyCFunctionWithKeywords = CALLBACK_FUNCTYPE(W_Object,
##                                            W_Object, W_Object, W_Object,
##                                            callconv=PyDLL)

class CConfig:
    _header_ = """
#include <Python.h>
#if PY_VERSION_HEX < 0x02050000   /* < 2.5 */
typedef int Py_ssize_t;
#endif
    """
    _include_dirs_ = [ctypes_platform.get_python_include_dir()]
    
    Py_ssize_t = ctypes_platform.SimpleType('Py_ssize_t')

    Py_LT = ctypes_platform.ConstantInteger('Py_LT')
    Py_LE = ctypes_platform.ConstantInteger('Py_LE')
    Py_EQ = ctypes_platform.ConstantInteger('Py_EQ')
    Py_NE = ctypes_platform.ConstantInteger('Py_NE')
    Py_GT = ctypes_platform.ConstantInteger('Py_GT')
    Py_GE = ctypes_platform.ConstantInteger('Py_GE')

##    PyMethodDef = ctypes_platform.Struct('PyMethodDef',
##                                         [('ml_name', c_char_p),
##                                          ('ml_meth', PyCFunction),
##                                          ('ml_flags', c_int),
##                                          ('ml_doc', c_char_p)])
##    METH_VARARGS = ctypes_platform.ConstantInteger('METH_VARARGS')

globals().update(ctypes_platform.configure(CConfig))
del CConfig


###########################################################
# ____________________ Object Protocol ____________________

PyObject_GetAttr = cpyapi.PyObject_GetAttr
PyObject_GetAttr.argtypes = [W_Object, W_Object]
PyObject_GetAttr.restype = W_Object

PyObject_GetItem = cpyapi.PyObject_GetItem
PyObject_GetItem.argtypes = [W_Object, W_Object]
PyObject_GetItem.restype = W_Object

PyObject_SetItem = cpyapi.PyObject_SetItem
PyObject_SetItem.argtypes = [W_Object, W_Object, W_Object]
PyObject_SetItem.restype = c_int

PyObject_Call = cpyapi.PyObject_Call
PyObject_Call.argtypes = [W_Object, W_Object, W_Object]
PyObject_Call.restype = W_Object

PyObject_CallFunctionObjArgs = cpyapi.PyObject_CallFunctionObjArgs
PyObject_CallFunctionObjArgs.restype = W_Object
#PyObject_CallFunctionObjArgs.argtypes = [W_Object, ..., final NULL]

PyObject_RichCompare = cpyapi.PyObject_RichCompare
PyObject_RichCompare.argtypes = [W_Object, W_Object, c_int]
PyObject_RichCompare.restype = W_Object

PyObject_RichCompareBool = cpyapi.PyObject_RichCompareBool
PyObject_RichCompareBool.argtypes = [W_Object, W_Object, c_int]
PyObject_RichCompareBool.restype = c_int

PyObject_GetIter = cpyapi.PyObject_GetIter
PyObject_GetIter.argtypes = [W_Object]
PyObject_GetIter.restype = W_Object

PyIter_Next = cpyapi.PyIter_Next
PyIter_Next.argtypes = [W_Object]
PyIter_Next.restype = W_Object


###########################################################
# ____________________ Number Protocol ____________________

PyNumber_Add = cpyapi.PyNumber_Add
PyNumber_Add.argtypes = [W_Object, W_Object]
PyNumber_Add.restype = W_Object

PyNumber_Subtract = cpyapi.PyNumber_Subtract
PyNumber_Subtract.argtypes = [W_Object, W_Object]
PyNumber_Subtract.restype = W_Object


#############################################################
# ____________________ Sequence Protocol ____________________

PySequence_Tuple = cpyapi.PySequence_Tuple
PySequence_Tuple.argtypes = [W_Object]
PySequence_Tuple.restype = W_Object

PySequence_SetItem = cpyapi.PySequence_SetItem
PySequence_SetItem.argtypes = [W_Object, Py_ssize_t, W_Object]
PySequence_SetItem.restype = c_int


###########################################################
# ____________________ Numeric Objects ____________________

PyInt_FromLong = cpyapi.PyInt_FromLong
PyInt_FromLong.argtypes = [c_long]
PyInt_FromLong.restype = W_Object

PyInt_AsLong = cpyapi.PyInt_AsLong
PyInt_AsLong.argtypes = [W_Object]
PyInt_AsLong.restype = c_long


###################################################
# ____________________ Strings ____________________

PyString_FromStringAndSize = cpyapi.PyString_FromStringAndSize
PyString_FromStringAndSize.argtypes = [c_char_p, Py_ssize_t]
PyString_FromStringAndSize.restype = W_Object

PyString_InternInPlace = cpyapi.PyString_InternInPlace
PyString_InternInPlace.argtypes = [POINTER(W_Object)]
PyString_InternInPlace.restype = None

PyString_AsString = cpyapi.PyString_AsString
PyString_AsString.argtypes = [W_Object]
PyString_AsString.restype = c_char_p


##################################################
# ____________________ Tuples ____________________

PyTuple_New = cpyapi.PyTuple_New
PyTuple_New.argtypes = [Py_ssize_t]
PyTuple_New.restype = W_Object


#################################################
# ____________________ Lists ____________________

PyList_New = cpyapi.PyList_New
PyList_New.argtypes = [Py_ssize_t]
PyList_New.restype = W_Object

PyList_Append = cpyapi.PyList_Append
PyList_Append.argtypes = [W_Object, W_Object]
PyList_Append.restype = c_int


########################################################
# ____________________ Dictionaries ____________________

PyDict_New = cpyapi.PyDict_New
PyDict_New.argtypes = []
PyDict_New.restype = W_Object

PyDict_SetItem = cpyapi.PyDict_SetItem
PyDict_SetItem.argtypes = [W_Object, W_Object, W_Object]
PyDict_SetItem.restype = c_int


#####################################################
# ____________________ Utilities ____________________

PyImport_ImportModule = cpyapi.PyImport_ImportModule
PyImport_ImportModule.argtypes = [c_char_p]
PyImport_ImportModule.restype = W_Object

# "RAW" because it comes from pythonapi instead of cpyapi
# which makes it raise the set exception directly instead
# of wrapping it into an OperationError
RAW_PyErr_SetObject = pythonapi.PyErr_SetObject
RAW_PyErr_SetObject.argtypes = [W_Object, W_Object]
RAW_PyErr_SetObject.restype = None


##############################################################
# ____________________ Built-in functions ____________________

PyArg_ParseTuple = cpyapi.PyArg_ParseTuple
PyArg_ParseTuple.restype = c_int
#PyArg_ParseTuple.argtypes = [W_Object, c_char_p, ...]

PyArg_ParseTupleAndKeywords = cpyapi.PyArg_ParseTupleAndKeywords
PyArg_ParseTupleAndKeywords.restype = c_int
#PyArg_ParseTupleAndKeywords.argtypes = [W_Object, W_Object,
#                                        c_char_p, POINTER(c_char_p), ...]

##PyCFunction_NewEx = cpyapi.PyCFunction_NewEx
##PyCFunction_NewEx.argtypes = [POINTER(PyMethodDef), W_Object, W_Object]
##PyCFunction_NewEx.restype = W_Object
