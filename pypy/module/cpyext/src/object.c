#include "Python.h"

/* Taken from cpython/Include/internal/pycore_object.h */

// Fast inlined version of PyType_HasFeature()
static inline int
_PyType_HasFeature(PyTypeObject *type, unsigned long feature) {
    return ((type->tp_flags & feature) != 0);
}


/* Inline functions trading binary compatibility for speed:
   _PyObject_Init() is the fast version of PyObject_Init(), and
   _PyObject_InitVar() is the fast version of PyObject_InitVar().

   These inline functions must not be called with op=NULL. */
static inline void
_PyObject_Init(PyObject *op, PyTypeObject *typeobj)
{
    assert(op != NULL);
    Py_SET_TYPE(op, typeobj);
    if (_PyType_HasFeature(typeobj, Py_TPFLAGS_HEAPTYPE)) {
        Py_INCREF(typeobj);
    }
    _Py_NewReference(op);
}

static inline void
_PyObject_InitVar(PyVarObject *op, PyTypeObject *typeobj, Py_ssize_t size)
{
    assert(op != NULL);
    Py_SET_SIZE(op, size);
    _PyObject_Init((PyObject *)op, typeobj);
}



/* Generic object operations; and implementation of None (NoObject) */

#include "Python.h"

extern void _PyPy_Free(void *ptr);
extern void *_PyPy_Malloc(Py_ssize_t size);

/* 
 * The actual value of this variable will be the address of
 * pyobject.w_marker_deallocating, and will be set by
 * pyobject.write_w_marker_deallocating().
 *
 * The value set here is used only as a marker by tests (because during the
 * tests we cannot call set_marker(), so we need to set a special value
 * directly here)
 */
void* _pypy_rawrefcount_w_marker_deallocating = (void*) 0xDEADFFF;

/* 
 * Mangle for translation.
 * For tests, we want to mangle as if they were c-api functions so
 * it will not be confused with the host's similarly named function
 */

#ifdef CPYEXT_TESTS
#define _Py_Dealloc _cpyexttest_Dealloc
#ifdef __GNUC__
__attribute__((visibility("default")))
#else
__declspec(dllexport)
#endif
#else  /* CPYEXT_TESTS */
#define _Py_Dealloc _PyPy_Dealloc
#endif  /* CPYEXT_TESTS */
void
_Py_Dealloc(PyObject *obj)
{
    PyTypeObject *pto = obj->ob_type;
    /* this is the same as rawrefcount.mark_deallocating() */
    obj->ob_pypy_link = (Py_ssize_t)_pypy_rawrefcount_w_marker_deallocating;
    pto->tp_dealloc(obj);
}

#ifdef CPYEXT_TESTS
#define _Py_object_dealloc _cpyexttest_object_dealloc
#ifdef __GNUC__
__attribute__((visibility("default")))
#else
__declspec(dllexport)
#endif
#else  /* CPYEXT_TESTS */
#define _Py_object_dealloc _PyPy_object_dealloc
#endif  /* CPYEXT_TESTS */
void
_Py_object_dealloc(PyObject *obj)
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

PyObject * _PyObject_GC_Malloc(size_t size)
{
    return (PyObject *)PyObject_Malloc(size);
}

PyObject * _PyObject_GC_New(PyTypeObject *type)
{
    return _PyObject_New(type);
}

PyVarObject * _PyObject_GC_NewVar(PyTypeObject *type, Py_ssize_t nitems)
{
    return _PyObject_NewVar(type, nitems);
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
PyObject_Init(PyObject *op, PyTypeObject *tp)
{
    if (op == NULL) {
        return PyErr_NoMemory();
    }

    _PyObject_Init(op, tp);
    return op;
}

PyVarObject *
PyObject_InitVar(PyVarObject *op, PyTypeObject *tp, Py_ssize_t size)
{
    if (op == NULL) {
        return (PyVarObject *) PyErr_NoMemory();
    }

    _PyObject_InitVar(op, tp, size);
    return op;
}

int
PyObject_CallFinalizerFromDealloc(PyObject *self)
{
    /* STUB */
    if (self->ob_type->tp_finalize) {
        fprintf(stderr, "WARNING: PyObject_CallFinalizerFromDealloc() "
                        "not implemented (objects of type '%s')\n",
                        self->ob_type->tp_name);
        self->ob_type->tp_finalize = NULL;   /* only once */
    }
    return 0;
}

const char *
_PyType_Name(PyTypeObject *type)
{
    assert(type->tp_name != NULL);
    const char *s = strrchr(type->tp_name, '.');
    if (s == NULL) {
        s = type->tp_name;
    }
    else {
        s++;
    }
    return s;
}

void
_Py_NewReference(PyObject *op)
{
#ifndef PYPY_VERSION
    if (_Py_tracemalloc_config.tracing) {
        _PyTraceMalloc_NewReference(op);
    }
#endif
#ifdef Py_REF_DEBUG
    _Py_RefTotal++;
#endif
    Py_SET_REFCNT(op, 1);
    ((PyObject *)(op))->ob_pypy_link = 0;
#ifdef Py_TRACE_REFS
    _Py_AddToAllObjects(op, 1);
#endif
}


