/* abi3/limited-API "unicodeerr" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_Create(const char *encoding, const char *object, Py_ssize_t length, Py_ssize_t start, Py_ssize_t end, const char *reason)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_Create() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_GetEncoding(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_GetEncoding() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_GetObject(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_GetObject() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyUnicodeDecodeError_GetStart(PyObject * _a0, Py_ssize_t * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_GetStart() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeDecodeError_GetEnd(PyObject * _a0, Py_ssize_t * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_GetEnd() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_GetReason(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_GetReason() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyUnicodeDecodeError_SetStart(PyObject * _a0, Py_ssize_t _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_SetStart() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeDecodeError_SetEnd(PyObject * _a0, Py_ssize_t _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_SetEnd() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeDecodeError_SetReason(PyObject *exc, const char *reason)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeDecodeError_SetReason() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyUnicodeEncodeError_GetEncoding(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_GetEncoding() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyUnicodeEncodeError_GetObject(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_GetObject() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyUnicodeEncodeError_GetStart(PyObject * _a0, Py_ssize_t * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_GetStart() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeEncodeError_GetEnd(PyObject * _a0, Py_ssize_t * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_GetEnd() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyUnicodeEncodeError_GetReason(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_GetReason() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyUnicodeEncodeError_SetStart(PyObject * _a0, Py_ssize_t _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_SetStart() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeEncodeError_SetEnd(PyObject * _a0, Py_ssize_t _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_SetEnd() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeEncodeError_SetReason(PyObject *exc, const char *reason)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeEncodeError_SetReason() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyUnicodeTranslateError_GetObject(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeTranslateError_GetObject() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyUnicodeTranslateError_GetStart(PyObject * _a0, Py_ssize_t * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeTranslateError_GetStart() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeTranslateError_GetEnd(PyObject * _a0, Py_ssize_t * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeTranslateError_GetEnd() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyUnicodeTranslateError_GetReason(PyObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeTranslateError_GetReason() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyUnicodeTranslateError_SetStart(PyObject * _a0, Py_ssize_t _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeTranslateError_SetStart() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeTranslateError_SetEnd(PyObject * _a0, Py_ssize_t _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeTranslateError_SetEnd() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyUnicodeTranslateError_SetReason(PyObject *exc, const char *reason)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicodeTranslateError_SetReason() is not implemented in PyPy");
    return -1;
}
