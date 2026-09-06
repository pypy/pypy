
#include "Python.h"

#ifdef MS_WINDOWS
#include "malloc.h" /* for alloca */
#include "windows.h"
#endif

int
PyRun_SimpleStringFlags(const char *command, PyCompilerFlags *flags)
{
    PyObject *m, *d, *v;
    m = PyImport_AddModule("__main__");
    if (m == NULL)
        return -1;
    d = PyModule_GetDict(m);            /* borrowed */
    v = PyRun_StringFlags(command, Py_file_input, d, d, flags);
    if (v == NULL) {
        PyErr_Print();
        return -1;
    }
    Py_DECREF(v);
    return 0;
}

#undef PyRun_SimpleString
int
PyRun_SimpleString(const char *command)
{
    return PyRun_SimpleStringFlags(command, NULL);
}

static void
_dump_extension_modules(FILE *out)
{
    PyObject *modules = PyImport_GetModuleDict();
    if (modules == NULL || !PyDict_Check(modules)) {
        return;
    }
    PyObject *stdlib_names = PySys_GetObject("stdlib_module_names");
    if (stdlib_names != NULL && !PyFrozenSet_Check(stdlib_names)) {
        stdlib_names = NULL;
    }

    PyObject *key, *value;
    Py_ssize_t pos = 0;
    int header = 1;
    Py_ssize_t count = 0;
    while (PyDict_Next(modules, &pos, &key, &value)) {
        if (!PyUnicode_Check(key) || !PyModule_Check(value)) {
            continue;
        }
        PyModuleDef *def = PyModule_GetDef(value);
        if (def == NULL || def->m_methods == NULL) {
            continue;
        }
        if (stdlib_names != NULL) {
            int is_stdlib = PySet_Contains(stdlib_names, key);
            if (is_stdlib < 0) {
                PyErr_Clear();
                is_stdlib = 0;
            }
            if (is_stdlib) {
                continue;
            }
        }
        if (header) {
            fprintf(out, "\nExtension modules: ");
            header = 0;
        }
        else {
            fprintf(out, ", ");
        }
        fprintf(out, "%s", PyUnicode_AsUTF8(key));
        count++;
    }
    if (count) {
        fprintf(out, " (total: %zd)\n", count);
    }
}

void
_Py_FatalErrorFunc(const char * func, const char *msg)
{
    if (func) {
        fprintf(stderr, "Fatal Python error: %s: %s\n", func, msg);
    }
    else {
        fprintf(stderr, "Fatal Python error: %s\n", msg);
    }
    fflush(stderr); /* it helps in Windows debug build */
    if (PyErr_Occurred()) {
        PyErr_PrintEx(0);
    }
    _dump_extension_modules(stderr);
#ifdef MS_WINDOWS
    {
        size_t len = strlen(msg);
        WCHAR* buffer;
        size_t i;

        /* Convert the message to wchar_t. This uses a simple one-to-one
        conversion, assuming that the this error message actually uses ASCII
        only. If this ceases to be true, we will have to convert. */
        buffer = alloca( (len+1) * (sizeof *buffer));
        for( i=0; i<=len; ++i)
            buffer[i] = msg[i];
        OutputDebugStringW(L"Fatal Python error: ");
        OutputDebugStringW(buffer);
        OutputDebugStringW(L"\n");
    }
#ifdef _DEBUG
    DebugBreak();
#endif
#endif /* MS_WINDOWS */
    abort();
}

/* Somewhere in the py3.10 development cycle, Py_FatalError became a macro that
 * uses __function__ to call _Py_FatalErrorFunc. But for backwards
 * compatiblity, export the old funcion from the shared object, both under
 * the PyPy-mangled name and under the bare name the stable ABI still has.
 */
#undef Py_FatalError

PyAPI_FUNC(void)
PyPy_FatalError(const char *msg)
{
    Py_FatalError(msg);
}

PyAPI_FUNC(void)
Py_FatalError(const char *msg)
{
    fprintf(stderr, "Fatal Python error: %s\n", msg);
    fflush(stderr); /* it helps in Windows debug build */
    if (PyErr_Occurred()) {
        PyErr_PrintEx(0);
    }
#ifdef MS_WINDOWS
    {
        size_t len = strlen(msg);
        WCHAR* buffer;
        size_t i;

        /* Convert the message to wchar_t. This uses a simple one-to-one
        conversion, assuming that the this error message actually uses ASCII
        only. If this ceases to be true, we will have to convert. */
        buffer = alloca( (len+1) * (sizeof *buffer));
        for( i=0; i<=len; ++i)
            buffer[i] = msg[i];
        OutputDebugStringW(L"Fatal Python error: ");
        OutputDebugStringW(buffer);
        OutputDebugStringW(L"\n");
    }
#ifdef _DEBUG
    DebugBreak();
#endif
#endif /* MS_WINDOWS */
    abort();
}

PyInterpreterState *
PyThreadState_GetInterpreter(PyThreadState *tstate)
{
    assert(tstate != NULL);
    return tstate->interp;
}
