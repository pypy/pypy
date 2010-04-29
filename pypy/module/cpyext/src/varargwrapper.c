#include <Python.h>
#include <stdarg.h>

PyObject * PyTuple_Pack(Py_ssize_t size, ...)
{
    va_list ap;
    PyObject *cur, *tuple;
    int i;

    tuple = PyTuple_New(size);
    va_start(ap, size);
    for (i = 0; i < size; i++) {
        cur = va_arg(ap, PyObject*);
        Py_INCREF(cur);
        if (PyTuple_SetItem(tuple, i, cur) < 0)
            return NULL;
    }
    va_end(ap);
    return tuple;
}

