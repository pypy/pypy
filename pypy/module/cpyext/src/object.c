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

void
_Py_Dealloc(PyObject *obj)
{
    PyTypeObject *pto = obj->ob_type;
    /* this is the same as rawrefcount.mark_deallocating() */
    obj->ob_pypy_link = _pypy_rawrefcount_w_marker_deallocating;
    pto->tp_dealloc(obj);
}

void
_PyPy_object_dealloc(PyObject *obj)
{
    PyTypeObject *pto;
    assert(obj->ob_refcnt == 0);
    pto = obj->ob_type;
    pto->tp_free(obj);
    if (pto->tp_flags & Py_TPFLAGS_HEAPTYPE)
        Py_DECREF(pto);
}

void
PyObject_Free(void *obj)
{
    free(obj);
}

void
PyObject_GC_Del(void *obj)
{
    free(obj);
}

PyObject *
PyType_GenericAlloc(PyTypeObject *type, Py_ssize_t nitems)
{
    return _PyObject_NewVar(type, nitems);
}
