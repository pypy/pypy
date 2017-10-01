/* Generic object operations; and implementation of None (NoObject) */

#include "Python.h"

void
Py_IncRef(PyObject *o)
{
    Py_XINCREF(o);
}

void
Py_DecRef(PyObject *o)
{
    Py_XDECREF(o);
}

Py_ssize_t _pypy_rawrefcount_w_marker_deallocating;  /* set from pyobject.py */

void _Py_Dealloc(PyObject *obj)
{
    PyTypeObject *pto = obj->ob_type;
    /* this is the same as rawrefcount.mark_deallocating() */
    obj->ob_pypy_link = _pypy_rawrefcount_w_marker_deallocating;
    pto->tp_dealloc(obj);
}
