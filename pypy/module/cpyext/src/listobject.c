#include "Python.h"

Py_ssize_t
_PyList_CheckExact(PyObject *op)
{
    return op->ob_type == &PyList_Type;
}