#include <Python.h>

int
PyErr_WarnFormat(PyObject *category, Py_ssize_t stack_level,
                 const char *format, ...)
{
    int ret;
    PyObject *message;
    va_list vargs;

#ifdef HAVE_STDARG_PROTOTYPES
    va_start(vargs, format);
#else
    va_start(vargs);
#endif
    message = PyUnicode_FromFormatV(format, vargs);
    if (message != NULL) {
        ret = PyErr_WarnEx(category, PyUnicode_AsUTF8(message), stack_level);
        Py_DECREF(message);
    }
    else
        ret = -1;
    va_end(vargs);
    return ret;
}

PyObject *
PyErr_FormatV(PyObject * exception, const char * format, va_list vargs) {
    PyObject * string = PyUnicode_FromFormatV(format, vargs);
    if (string != NULL) {
        PyErr_SetObject(exception, string);
    }
    return NULL;
}
