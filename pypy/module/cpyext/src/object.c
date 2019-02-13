/* Generic object operations; and implementation of None (NoObject) */

#include "Python.h"

/* Get an object's GC head */
#define AS_GC(o) ((PyGC_Head *)(o)-1)

/* Get the object given the GC head */
#define FROM_GC(g) ((PyObject *)(((PyGC_Head *)g)+1))

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

/* 
 * The actual value of this variable will be the address of
 * pyobject.w_marker_deallocating, and will be set by
 * pyobject.write_w_marker_deallocating().
 *
 * The value set here is used only as a marker by tests (because during the
 * tests we cannot call set_marker(), so we need to set a special value
 * directly here)
 */
Py_ssize_t _pypy_rawrefcount_w_marker_deallocating = 0xDEADFFF;

static PyGC_Head _internal_pyobj_list;
PyGC_Head *_pypy_rawrefcount_pyobj_list = &_internal_pyobj_list;

PyGC_Head *
_PyPy_init_pyobj_list()
{
    _pypy_rawrefcount_pyobj_list->gc_next = _pypy_rawrefcount_pyobj_list;
    _pypy_rawrefcount_pyobj_list->gc_prev = _pypy_rawrefcount_pyobj_list;
    return _pypy_rawrefcount_pyobj_list;
}

GCHdr_PyObject *
_PyPy_gc_as_pyobj(PyGC_Head *g)
{
    return (GCHdr_PyObject *)FROM_GC(g);
}

PyGC_Head *
_PyPy_pyobj_as_gc(GCHdr_PyObject *obj)
{
    if (PyType_IS_GC(((PyObject *)obj)->ob_type)) {
        return AS_GC(obj);
    } else {
        return NULL;
    }
}

Py_ssize_t
_PyPy_finalizer_type(PyGC_Head *g)
{
    return 0;
}

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
PyObject_GC_Track(void *obj)
{
    _PyObject_GC_TRACK(obj);
}

void
PyObject_GC_UnTrack(void *obj)
{
    if (_PyGC_IS_TRACKED(obj))
        _PyObject_GC_UNTRACK(obj);
}

void
PyObject_GC_Del(void *obj)
{
    PyGC_Head *g = AS_GC(obj);
    if (_PyGC_IS_TRACKED(obj))
        _PyObject_GC_UNTRACK(obj);
    _PyPy_Free(g);
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

static PyObject *
_generic_gc_alloc(PyTypeObject *type, Py_ssize_t nitems)
{
    Py_ssize_t size;
    PyObject *pyobj;
    PyGC_Head *g;
    if (type->tp_flags & Py_TPFLAGS_HEAPTYPE)
        Py_INCREF(type);

    size = sizeof(PyGC_Head) + type->tp_basicsize;
    if (type->tp_itemsize)
        size += nitems * type->tp_itemsize;

    g = (PyGC_Head*)_PyPy_Malloc(size);
    if (g == NULL)
        return NULL;
    g->gc_refs = 0;
    _PyGCHead_SET_REFS(g, _PyGC_REFS_UNTRACKED);

    pyobj = FROM_GC(g);
    if (type->tp_itemsize)
        ((PyVarObject*)pyobj)->ob_size = nitems;

    pyobj->ob_refcnt = 1;
    /* pyobj->ob_pypy_link should get assigned very quickly */
    pyobj->ob_type = type;
    return pyobj;
}


PyObject * _PyObject_GC_New(PyTypeObject *type)
{
    return (PyObject*)_PyObject_GC_NewVar(type, 0);
}

PyVarObject * _PyObject_GC_NewVar(PyTypeObject *type, Py_ssize_t nitems)
{
    PyObject *py_obj = _generic_gc_alloc(type, nitems);
    if (!py_obj)
        return (PyVarObject*)PyErr_NoMemory();

    if (type->tp_itemsize == 0)
        return (PyVarObject*)PyObject_INIT(py_obj, type);
    else
        return PyObject_INIT_VAR((PyVarObject*)py_obj, type, nitems);
}

static PyObject *
_generic_alloc(PyTypeObject *type, Py_ssize_t nitems)
{
    Py_ssize_t size;
    PyObject *pyobj;
    if (type->tp_flags & Py_TPFLAGS_HEAPTYPE)
        Py_INCREF(type);

    size = type->tp_basicsize;
    if (type->tp_itemsize)
        size += nitems * type->tp_itemsize;

    pyobj = (PyObject*)_PyPy_Malloc(size);
    if (pyobj == NULL)
        return NULL;

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
    PyObject *py_obj = _generic_alloc(type, nitems);
    if (!py_obj)
        return (PyVarObject*)PyErr_NoMemory();
    
    if (type->tp_itemsize == 0)
        return (PyVarObject*)PyObject_INIT(py_obj, type);
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
    return (PyVarObject*)PyObject_Init((PyObject*)obj, type);
}
