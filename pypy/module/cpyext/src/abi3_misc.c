/* abi3/limited-API "misc" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

/* Stable-ABI entry points that the headers otherwise provide as macros or
   static inlines for code compiled against PyPy; abi3 wheels compiled
   against CPython's headers reference the exported functions instead. */

#undef Py_NewRef
PyAPI_FUNC(PyObject*) Py_NewRef(PyObject *obj)
{
    return _Py_NewRef(obj);
}

#undef Py_XNewRef
PyAPI_FUNC(PyObject*) Py_XNewRef(PyObject *obj)
{
    return _Py_XNewRef(obj);
}

#undef PyObject_GC_Track
PyAPI_FUNC(void) PyObject_GC_Track(void *op)
{
}

#undef PyObject_GC_UnTrack
PyAPI_FUNC(void) PyObject_GC_UnTrack(void *op)
{
}

#undef PyVectorcall_NARGS
PyAPI_FUNC(Py_ssize_t) PyVectorcall_NARGS(size_t nargsf)
{
    return _PyVectorcall_NARGS(nargsf);
}

#undef Py_CompileString
PyAPI_FUNC(PyObject *) Py_CompileString(const char *str, const char *filename, int start)
{
    return Py_CompileStringFlags(str, filename, start, NULL);
}

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

PyAPI_FUNC(PyCodeObject *) PyFrame_GetCode(PyFrameObject *frame)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyFrame_GetCode() is not implemented in PyPy");
    return NULL;
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
