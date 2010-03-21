#include <pypy_rename.h>
#include <Python.h>
#include <stdarg.h>

PyObject * PyTuple_Pack(Py_ssize_t size, ...)
{
    va_list ap;
    PyObject *cur, *tuple;
    int i;

    tuple = PyTuple_New(size);
    va_start(ap, size);
    for (i = 0; i < size; cur = va_arg(ap, PyObject*)) {
        Py_INCREF(cur);
        PyTuple_SetItem(tuple, i, cur);
    }
    va_end(ap);
    return tuple;
}

