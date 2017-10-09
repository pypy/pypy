/* Generic object operations; and implementation of None (NoObject) */

#include "Python.h"

extern void _PyPy_Free(void *ptr);
extern void *_PyPy_Malloc(Py_ssize_t size);

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
    _PyPy_Free(obj);
}

void
PyObject_GC_Del(void *obj)
{
    _PyPy_Free(obj);
}

PyObject *
PyType_GenericAlloc(PyTypeObject *type, Py_ssize_t nitems)
{
    return (PyObject*)_PyObject_NewVar(type, nitems);
}

PyObject *
_PyObject_New(PyTypeObject *type)
{
    return (PyObject*)_PyObject_NewVar(type, 0);
}

PyObject * _PyObject_GC_New(PyTypeObject *type)
{
    return _PyObject_New(type);
}


static PyObject *
_type_alloc(PyTypeObject *metatype)
{
    PyHeapTypeObject *heaptype = (PyHeapTypeObject*)_PyPy_Malloc(sizeof(PyTypeObject));
    PyTypeObject *pto = &heaptype->ht_type;

    pto->ob_refcnt = 1;
    pto->ob_pypy_link = 0;
    pto->ob_type = metatype;
    pto->tp_flags |= Py_TPFLAGS_HEAPTYPE;
    pto->tp_as_number = &heaptype->as_number;
    pto->tp_as_sequence = &heaptype->as_sequence;
    pto->tp_as_mapping = &heaptype->as_mapping;
    pto->tp_as_buffer = &heaptype->as_buffer;
    pto->tp_basicsize = -1; /* hopefully this makes malloc bail out */
    pto->tp_itemsize = 0;
    return (PyObject*)heaptype;
}

static PyObject *
_generic_alloc(PyTypeObject *type, Py_ssize_t nitems)
{
    if (type->tp_flags & Py_TPFLAGS_HEAPTYPE)
        Py_INCREF(type);

    Py_ssize_t size = type->tp_basicsize;
    if (type->tp_itemsize)
        size += nitems * type->tp_itemsize;

    PyObject *pyobj = (PyObject*)_PyPy_Malloc(size);
    
    if (type->tp_itemsize)
        ((PyVarObject*)pyobj)->ob_size = nitems;

    pyobj->ob_refcnt = 1;
    /* pyobj->ob_pypy_link should get assigned very quickly */
    pyobj->ob_type = type;
    return pyobj;
}

PyVarObject *
_PyObject_NewVar(PyTypeObject *type, Py_ssize_t nitems)
{
    /* Note that this logic is slightly different than the one used by
       CPython. The plan is to try to follow as closely as possible the
       current cpyext logic here, and fix it when the migration to C is
       completed
    */
    PyObject *py_obj;
    if (type == &PyType_Type)
        py_obj = _type_alloc(type);
    else
        py_obj = _generic_alloc(type, nitems);

    if (!py_obj)
        return (PyVarObject*)PyErr_NoMemory();
    
    if (type->tp_itemsize == 0)
        return PyObject_INIT(py_obj, type);
    else
        return PyObject_INIT_VAR((PyVarObject*)py_obj, type, nitems);
}

PyObject *
PyObject_Init(PyObject *obj, PyTypeObject *type)
{
    obj->ob_type = type;
    obj->ob_pypy_link = 0;
    obj->ob_refcnt = 1;
    return obj;
}

PyVarObject *
PyObject_InitVar(PyVarObject *obj, PyTypeObject *type, Py_ssize_t size)
{
    obj->ob_size = size;
    return PyObject_Init((PyObject*)obj, type);
}
