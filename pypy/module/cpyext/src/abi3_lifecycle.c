/* abi3/limited-API "lifecycle" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

PyAPI_FUNC(void) Py_Initialize(void)
{

}

PyAPI_FUNC(void) Py_InitializeEx(int _a0)
{

}

PyAPI_FUNC(void) Py_Finalize(void)
{

}

PyAPI_FUNC(int) Py_FinalizeEx(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_FinalizeEx() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(void) Py_Exit(int status)
{
    exit(status);
}

PyAPI_FUNC(int) Py_Main(int argc, wchar_t **argv)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_Main() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) Py_BytesMain(int argc, char **argv)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_BytesMain() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyInterpreterState *) PyInterpreterState_New(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyInterpreterState_New() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyInterpreterState *) PyInterpreterState_Get(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyInterpreterState_Get() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyInterpreterState_GetDict(PyInterpreterState * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyInterpreterState_GetDict() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(void) PyInterpreterState_Clear(PyInterpreterState * _a0)
{

}

PyAPI_FUNC(void) PyInterpreterState_Delete(PyInterpreterState * _a0)
{

}

PyAPI_FUNC(wchar_t *) Py_GetPath(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetPath() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(wchar_t *) Py_GetPrefix(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetPrefix() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(wchar_t *) Py_GetExecPrefix(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetExecPrefix() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(wchar_t *) Py_GetProgramFullPath(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetProgramFullPath() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(wchar_t *) Py_GetPythonHome(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetPythonHome() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(const char *) Py_GetPlatform(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetPlatform() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(const char *) Py_GetCompiler(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetCompiler() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(const char *) Py_GetCopyright(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetCopyright() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(const char *) Py_GetBuildInfo(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_GetBuildInfo() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(void) Py_SetPath(const wchar_t * _a0)
{

}

PyAPI_FUNC(void) Py_SetProgramName(const wchar_t * _a0)
{

}

PyAPI_FUNC(void) Py_SetPythonHome(const wchar_t * _a0)
{

}

PyAPI_FUNC(wchar_t *) Py_DecodeLocale(const char *arg, size_t *size)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_DecodeLocale() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(char*) Py_EncodeLocale(const wchar_t *text, size_t *error_pos)
{
    PyErr_SetString(PyExc_NotImplementedError, "Py_EncodeLocale() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyEval_EvalFrame(PyFrameObject * _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyEval_EvalFrame() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyEval_EvalFrameEx(PyFrameObject *f, int exc)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyEval_EvalFrameEx() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(void) PyEval_AcquireLock(void)
{

}

PyAPI_FUNC(void) PyEval_ReleaseLock(void)
{

}
