
#include "Python.h"

#ifdef MS_WINDOWS
#include "malloc.h" /* for alloca */
#include "windows.h"
#endif

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
 * compatiblity, export the old funcion from the shared object
 */
PyAPI_FUNC(void)
PyPy_FatalError(const char *msg)
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
