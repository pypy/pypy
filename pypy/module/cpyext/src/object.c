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

/* ob_pypy_link is stored in a hidden prefix word immediately before the visible
   PyObject header (see include/cpyext_object.h), so the header matches CPython for
   abi3.  Every PyObject allocation reserves this prefix and hands out a pointer past
   it; PyObject_GC_Del (and the default tp_free) release it.  Internal only -- never
   exposed to extensions.  Similar to PyGC_HEAD in CPython. */
#define _PyPy_LINK_PREFIX  (sizeof(Py_ssize_t))
#define _PyPy_LINK(op)     (((Py_ssize_t *)(op))[-1])

/* Refcount tag constants -- MUST match rpython/rlib/rawrefcount.py exactly.
   REFCNT_FROM_PYPY is the permanent "this PyObject has a prefix" tag applied
   at allocation; an object is owned iff ob_refcnt >= REFCNT_FROM_PYPY.  It
   sits above the _Py_IMMORTAL_REFCNT field (low 32 bits on 64-bit, low 30 on
   32-bit), so immortality (checked with _Py_IsImmortal, see include/object.h)
   is orthogonal to the tag: an immortalized owned object has
   ob_refcnt == REFCNT_FROM_PYPY + _Py_IMMORTAL_REFCNT.
   See pypy/doc/discussion/rawrefcount.rst. */
#if SIZEOF_VOID_P > 4
#define _PyPy_REFCNT_FROM_PYPY        ((Py_ssize_t)(PY_SSIZE_T_MAX / 4 + 1))
#define _PyPy_REFCNT_FROM_PYPY_LIGHT  ((Py_ssize_t)(_PyPy_REFCNT_FROM_PYPY + (PY_SSIZE_T_MAX / 2 + 1)))
#else
#define _PyPy_REFCNT_FROM_PYPY        ((Py_ssize_t)0x40000000)
#define _PyPy_REFCNT_FROM_PYPY_LIGHT  ((Py_ssize_t)0x70000000)
#endif

/* The word before the link is padding (it keeps ob_refcnt 16-byte aligned),
   and holds cpyext's own per-object flags, like the bits CPython keeps in
   PyGC_Head.ob_prev.  Only objects allocated through _PyPy_Malloc have the
   prefix, which is what the REFCNT_FROM_PYPY tag marks; a statically
   allocated or extension-malloc'd object has neither, so the flags are
   read as 0 and writing them is skipped. */
#define _PyPy_FLAGS(op)        (((Py_ssize_t *)(op))[-2])
#define _PyPy_HAS_PREFIX(op)   ((op)->ob_refcnt >= _PyPy_REFCNT_FROM_PYPY)
#define _PyPy_FLAG_FINALIZED   1

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

#ifdef CPYEXT_TESTS
#ifdef __GNUC__
__attribute__((visibility("default")))
#else
__declspec(dllexport)
#endif
#endif  /* CPYEXT_TESTS */
void
_Py_Dealloc(PyObject *obj)
{
    PyTypeObject *pto = obj->ob_type;
    /* Only owned objects (refcnt >= REFCNT_FROM_PYPY here) have a prefix link word
       to mark.  Foreign objects -- bare-allocated by an extension, refcnt below the
       tag -- have no prefix; writing it would corrupt the heap word before them. */
    if (obj->ob_refcnt >= _PyPy_REFCNT_FROM_PYPY)
        _PyPy_LINK(obj) = (Py_ssize_t)_pypy_rawrefcount_w_marker_deallocating;
    pto->tp_dealloc(obj);
}

/* Py_INCREF/Py_DECREF route here (see include/object.h) so the REFCNT_FROM_PYPY tag
   and the prefix stay out of extension-visible code.  Deallocation fires on either
   condition: refcnt hits 0 (foreign/untagged) or refcnt falls to the bare tag with no
   w_obj left (owned, no C refs, ob_pypy_link == 0).  The prefix is only read once
   refcnt == REFCNT_FROM_PYPY, which a foreign object never reaches. */
void
_Py_IncRef(PyObject *op)
{
    if (_Py_IsImmortal(op))
        return;   /* immortal: refcnt pinned */
    op->ob_refcnt++;
}

void
_Py_DecRef(PyObject *op)
{
    if (_Py_IsImmortal(op))
        return;   /* immortal: refcnt pinned, never freed */
    if (--op->ob_refcnt == 0)
        _Py_Dealloc(op);
    else if (op->ob_refcnt == _PyPy_REFCNT_FROM_PYPY && _PyPy_LINK(op) == 0)
        _Py_Dealloc(op);
}

#ifdef CPYEXT_TESTS
#ifdef __GNUC__
__attribute__((visibility("default")))
#else
__declspec(dllexport)
#endif
#endif  /* CPYEXT_TESTS */
void
_Py_object_dealloc(PyObject *obj)
{
    PyTypeObject *pto;
    assert(obj->ob_refcnt == 0 || obj->ob_refcnt == _PyPy_REFCNT_FROM_PYPY);
    pto = obj->ob_type;
    /* like CPython's object_dealloc, this does not decref the type: that is
       _Py_subtype_dealloc's job */
    pto->tp_free(obj);
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
    PyObject *pyobj;
    /* the Py_TPFLAGS_HEAPTYPE incref is left to _PyObject_Init, which the
       only caller runs right after this, like CPython's tp_alloc does */
    const size_t size = _PyObject_VAR_SIZE(type, nitems+1);
    /* note that we need to add one, for the sentinel */

    pyobj = (PyObject*)_PyPy_Malloc(size);
    if (pyobj == NULL)
        return NULL;

    if (type->tp_itemsize)
        ((PyVarObject*)pyobj)->ob_size = nitems;

    pyobj->ob_refcnt = _PyPy_REFCNT_FROM_PYPY;
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

/* tp_finalize runs at most once per object, as in CPython: the flag is also
   read and set by cpyext's __del__ wrapper (slotdefs.wrap_del), which is how
   PyPy's own finalizer reaches tp_finalize for an object it owns. */
static void
_PyPy_CallFinalizer(PyObject *self)
{
    PyTypeObject *tp = Py_TYPE(self);

    if (tp->tp_finalize == NULL)
        return;
    if (!_PyPy_HAS_PREFIX(self)) {
        /* no prefix to remember it in: the object was never seen by PyPy, so
           this is the only path that can call its finalizer */
        tp->tp_finalize(self);
        return;
    }
    if (_PyPy_FLAGS(self) & _PyPy_FLAG_FINALIZED)
        return;
    _PyPy_FLAGS(self) |= _PyPy_FLAG_FINALIZED;
    tp->tp_finalize(self);
}

int
PyObject_CallFinalizerFromDealloc(PyObject *self)
{
    _PyPy_CallFinalizer(self);
    /* CPython returns -1 for an object the finalizer resurrected, and its
       caller then stops deallocating.  PyPy cannot honour that: an owned
       object's w_obj is already marked dying by _Py_Dealloc, and any attempt
       to reach the object from PyPy again fatalerrors in from_ref ("Invalid
       usage of a dying CPython object").  So resurrection is unsupported and
       deallocation always continues. */
    return 0;
}

int
PyObject_GC_IsFinalized(PyObject *op)
{
    /* cpyext remembers the flag for every object it allocated, but CPython
       keeps it in the GC head and so reports 0 for a type without
       Py_TPFLAGS_HAVE_GC */
    if (!_PyType_HasFeature(Py_TYPE(op), Py_TPFLAGS_HAVE_GC))
        return 0;
    if (!_PyPy_HAS_PREFIX(op))
        return 0;
    return (_PyPy_FLAGS(op) & _PyPy_FLAG_FINALIZED) != 0;
}

void
PyObject_ClearWeakRefs(PyObject *object)
{
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

PyObject *
PyType_GetName(PyTypeObject *type)
{
    if (type->tp_flags & Py_TPFLAGS_HEAPTYPE) {
        PyHeapTypeObject* et = (PyHeapTypeObject*)type;

        Py_INCREF(et->ht_name);
        return et->ht_name;
    }
    else {
        return PyUnicode_FromString(_PyType_Name(type));
    }
}


PyObject *
PyType_GetQualName(PyTypeObject *type)
{
    if (type->tp_flags & Py_TPFLAGS_HEAPTYPE) {
        PyHeapTypeObject* et = (PyHeapTypeObject*)type;
        Py_INCREF(et->ht_qualname);
        return et->ht_qualname;
    }
    else {
        return PyUnicode_FromString(_PyType_Name(type));
    }
}


int
_PyObject_VisitManagedDict(PyObject *obj, visitproc visit, void *arg)
{
    PyTypeObject *tp = Py_TYPE(obj);
    if ((tp->tp_flags & Py_TPFLAGS_MANAGED_DICT) == 0 || !tp->tp_dictoffset
            || tp->tp_dictoffset == MANAGED_DICT_OFFSET) {
        return 0;
    }
    Py_ssize_t dictoffset = tp->tp_dictoffset;
    if (dictoffset < 0) {
        dictoffset += tp->tp_basicsize;
    }
    PyObject **dictptr = (PyObject **)((char *)obj + dictoffset);
    if (*dictptr != NULL) {
        int vret = visit(*dictptr, arg);
        if (vret)
            return vret;
    }
    return 0;
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
    op->ob_refcnt++;
#ifdef Py_TRACE_REFS
    _Py_AddToAllObjects(op, 1);
#endif
}


