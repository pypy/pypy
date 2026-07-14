/* abi3/limited-API "sysimport" shims for functions PyPy does not implement.
   error shims set NotImplementedError and return an error sentinel;
   ignore shims are no-ops. */

#include "Python.h"

PyAPI_FUNC(void) PySys_SetArgv(int _a0, wchar_t ** _a1)
{

}

PyAPI_FUNC(void) PySys_SetArgvEx(int _a0, wchar_t ** _a1, int _a2)
{

}

PyAPI_FUNC(void) PySys_SetPath(const wchar_t * _a0)
{

}

PyAPI_FUNC(void) PySys_AddXOption(const wchar_t * _a0)
{

}

PyAPI_FUNC(PyObject *) PySys_GetXOptions(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PySys_GetXOptions() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(void) PySys_AddWarnOption(const wchar_t * _a0)
{

}

PyAPI_FUNC(void) PySys_AddWarnOptionUnicode(PyObject * _a0)
{

}

PyAPI_FUNC(void) PySys_ResetWarnOptions(void)
{

}

PyAPI_FUNC(int) PySys_HasWarnOptions(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PySys_HasWarnOptions() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(void) PySys_FormatStderr(const char *format, ...)
{

}

PyAPI_FUNC(void) PySys_FormatStdout(const char *format, ...)
{

}

PyAPI_FUNC(PyObject *) PyImport_AddModuleObject(PyObject *name)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_AddModuleObject() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyImport_AppendInittab(const char *name, PyObject* (*initfunc)(void))
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_AppendInittab() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject *) PyImport_ExecCodeModuleObject(PyObject *name, PyObject *co, PyObject *pathname, PyObject *cpathname)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_ExecCodeModuleObject() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyImport_ExecCodeModuleWithPathnames(const char *name, PyObject *co, const char *pathname, const char *cpathname)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_ExecCodeModuleWithPathnames() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(PyObject *) PyImport_GetImporter(PyObject *path)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_GetImporter() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(long) PyImport_GetMagicNumber(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_GetMagicNumber() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(const char *) PyImport_GetMagicTag(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_GetMagicTag() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(int) PyImport_ImportFrozenModule(const char *name)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_ImportFrozenModule() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyImport_ImportFrozenModuleObject(PyObject *name)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyImport_ImportFrozenModuleObject() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(PyObject*) PyThread_GetInfo(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyThread_GetInfo() is not implemented in PyPy");
    return NULL;
}

PyAPI_FUNC(size_t) PyThread_get_stacksize(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyThread_get_stacksize() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyThread_set_stacksize(size_t _a0)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyThread_set_stacksize() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(unsigned long) PyThread_get_thread_native_id(void)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyThread_get_thread_native_id() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(void) PyOS_BeforeFork(void)
{

}

PyAPI_FUNC(void) PyOS_AfterFork_Parent(void)
{

}

PyAPI_FUNC(void) PyOS_AfterFork_Child(void)
{

}

PyAPI_FUNC(int) PyOS_mystricmp(const char * _a0, const char * _a1)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyOS_mystricmp() is not implemented in PyPy");
    return -1;
}

PyAPI_FUNC(int) PyOS_mystrnicmp(const char * _a0, const char * _a1, Py_ssize_t _a2)
{
    PyErr_SetString(PyExc_NotImplementedError, "PyOS_mystrnicmp() is not implemented in PyPy");
    return -1;
}
