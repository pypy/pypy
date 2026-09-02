/* abi3/limited-API "codecs" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

PyAPI_FUNC(int) PyCodec_Register(PyObject *search_function)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_Register() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyCodec_Unregister(PyObject *search_function)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_Unregister() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyCodec_RegisterError(const char *name, PyObject *error)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_RegisterError() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyCodec_LookupError(const char *name)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_LookupError() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyCodec_KnownEncoding(const char *encoding)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_KnownEncoding() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyCodec_StrictErrors(PyObject *exc)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_StrictErrors() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyCodec_IgnoreErrors(PyObject *exc)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_IgnoreErrors() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyCodec_ReplaceErrors(PyObject *exc)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_ReplaceErrors() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyCodec_XMLCharRefReplaceErrors(PyObject *exc)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_XMLCharRefReplaceErrors() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyCodec_BackslashReplaceErrors(PyObject *exc)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_BackslashReplaceErrors() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyCodec_NameReplaceErrors(PyObject *exc)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_NameReplaceErrors() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyCodec_StreamReader(const char *encoding, PyObject *stream, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_StreamReader() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyCodec_StreamWriter(const char *encoding, PyObject *stream, const char *errors)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyCodec_StreamWriter() is not implemented in PyPy");
    return NULL;
}
