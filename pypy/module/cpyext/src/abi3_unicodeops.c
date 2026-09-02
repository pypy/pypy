/* abi3/limited-API "unicodeops" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

PyAPI_FUNC(PyObject*) PyUnicode_Partition(PyObject *s, PyObject *sep)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_Partition() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_RPartition(PyObject *s, PyObject *sep)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_RPartition() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_RSplit(PyObject *s, PyObject *sep, Py_ssize_t maxsplit)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_RSplit() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyUnicode_Translate(PyObject *str, PyObject *table, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_Translate() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyUnicode_RichCompare(PyObject *left, PyObject *right, int op)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_RichCompare() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyUnicode_IsIdentifier(PyObject *s)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_IsIdentifier() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject*) PyUnicode_AsCharmapString(PyObject *unicode, PyObject *mapping)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_AsCharmapString() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_DecodeCharmap(const char *string, Py_ssize_t length, PyObject *mapping, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_DecodeCharmap() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_BuildEncodingMap(PyObject* string)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_BuildEncodingMap() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_AsDecodedObject(PyObject *unicode, const char *encoding, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_AsDecodedObject() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_AsDecodedUnicode(PyObject *unicode, const char *encoding, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_AsDecodedUnicode() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_AsEncodedUnicode(PyObject *unicode, const char *encoding, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_AsEncodedUnicode() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_DecodeUnicodeEscape(const char *string, Py_ssize_t length, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_DecodeUnicodeEscape() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF7(const char *string, Py_ssize_t length, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_DecodeUTF7() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF7Stateful(const char *string, Py_ssize_t length, const char *errors, Py_ssize_t *consumed)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_DecodeUTF7Stateful() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF8Stateful(const char *string, Py_ssize_t length, const char *errors, Py_ssize_t *consumed)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_DecodeUTF8Stateful() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF16Stateful(const char *string, Py_ssize_t length, const char *errors, int *byteorder, Py_ssize_t *consumed)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_DecodeUTF16Stateful() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF32Stateful(const char *string, Py_ssize_t length, const char *errors, int *byteorder, Py_ssize_t *consumed)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyUnicode_DecodeUTF32Stateful() is not implemented in PyPy");
    return NULL;
}
