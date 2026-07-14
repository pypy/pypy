/* abi3/limited-API "misc" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

PyAPI_FUNC(int) PyAIter_Check(PyObject * _a0)
{
    return 0;
}

PyAPI_FUNC(int) PyDict_MergeFromSeq2(PyObject *d, PyObject *seq2, int override)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyDict_MergeFromSeq2() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyCFunction_GetFlags(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCFunction_GetFlags() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyCFunction_GetSelf(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCFunction_GetSelf() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyFloat_GetInfo(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyFloat_GetInfo() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(double) PyFloat_GetMin(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyFloat_GetMin() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(double) PyFloat_GetMax(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyFloat_GetMax() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyCodeObject *) PyFrame_GetCode(PyFrameObject *frame)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyFrame_GetCode() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyException_GetArgs(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyException_GetArgs() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(void) PyException_SetArgs(PyObject * _a0, PyObject * _a1)
{

}

PyAPI_FUNC(const char *) PyExceptionClass_Name(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyExceptionClass_Name() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(const char *) PyModule_GetFilename(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyModule_GetFilename() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyModule_SetDocString(PyObject * _a0, const char * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyModule_SetDocString() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyMember_GetOne(const char * _a0, PyMemberDef * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyMember_GetOne() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyMember_SetOne(char * _a0, PyMemberDef * _a1, PyObject * _a2)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyMember_SetOne() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyDescr_NewMember(PyTypeObject * _a0, PyMemberDef * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyDescr_NewMember() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyLong_GetInfo(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyLong_GetInfo() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyObject_CopyData(PyObject *dest, PyObject *src)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyObject_CopyData() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyObject_GetAIter(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyObject_GetAIter() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(Py_ssize_t) PySequence_Count(PyObject *o, PyObject *value)
{
    PyErr_SetString(PyExc_NotImplementedError, "PySequence_Count() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PySequence_In(PyObject *o, PyObject *value)
{
    PyErr_SetString(PyExc_NotImplementedError, "PySequence_In() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyWrapper_New(PyObject * _a0, PyObject * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyWrapper_New() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyBytes_Repr(PyObject * _a0, int _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyBytes_Repr() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyBytes_DecodeEscape(const char * _a0, Py_ssize_t _a1, const char * _a2, Py_ssize_t _a3, const char * _a4)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyBytes_DecodeEscape() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(Py_ssize_t) PyBuffer_SizeFromFormat(const char *format)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyBuffer_SizeFromFormat() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(void) PyBuffer_FillContiguousStrides(int ndims, Py_ssize_t *shape, Py_ssize_t *strides, int itemsize, char fort)
{

}

PyAPI_FUNC(PyObject *) PyErr_ProgramText(const char *filename, int lineno)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyErr_ProgramText() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyErr_ResourceWarning(PyObject *source, Py_ssize_t stack_level, const char *format, ...)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyErr_ResourceWarning() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyErr_SetImportError(PyObject * _a0, PyObject * _a1, PyObject * _a2)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyErr_SetImportError() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyErr_SetImportErrorSubclass(PyObject * _a0, PyObject * _a1, PyObject * _a2, PyObject * _a3)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyErr_SetImportErrorSubclass() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(void) PyErr_SyntaxLocation(const char *filename, int lineno)
{

}

PyAPI_FUNC(void) PyErr_SyntaxLocationEx(const char *filename, int lineno, int col_offset)
{

}
