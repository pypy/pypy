/* Generic object operations; and implementation of None (NoObject) */

#include "Python.h"

void
Py_DecRef(PyObject *o)
{
    Py_XDECREF(o);
}

