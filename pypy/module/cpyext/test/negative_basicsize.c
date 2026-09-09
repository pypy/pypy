/*
 * Reproducer for a nanobind crash on PyPy 3.12.
 *
 * This mirrors nanobind's emulated PyType_FromMetaclass() in
 * src/nb_type.cpp (nb_type_from_metaclass, used whenever
 * NB_TYPE_FROM_METACLASS_IMPL == 1, i.e. on every PyPy): allocate a heap
 * type with PyType_GenericAlloc(&PyType_Type, 0), fill it in by hand, store
 * a *negative* (base-relative) basicsize into tp_basicsize, and call
 * PyType_Ready().
 *
 * PyType_Ready() used to silently replace the negative tp_basicsize with
 * the inherited base size, so instances of the metaclass were allocated
 * without the extra bytes and writes into that area overran the heap block.
 * CPython leaves the value alone and fails with MemoryError when an
 * instance is allocated; PyPy resolves it like PyType_FromMetaclass does
 * (PEP 697), so the extra bytes really are there.
 *
 * Returns a dict so the caller can check the numbers:
 *   basicsize_before_ready: value we stored (negative)
 *   basicsize_after_ready:  what PyType_Ready left in tp_basicsize
 *   base_basicsize:         PyType_Type.tp_basicsize
 *   expected:               what PyType_FromMetaclass would produce
 *                           (both parts rounded up to ALIGNOF_MAX_ALIGN_T)
 */
#include <Python.h>

#define ALIGN_UP(n) (((n) + ALIGNOF_MAX_ALIGN_T - 1) & ~(ALIGNOF_MAX_ALIGN_T - 1))

static PyObject *
make_meta(PyObject *self, PyObject *args)
{
    int extra;
    if (!PyArg_ParseTuple(args, "i", &extra))
        return NULL;

    PyObject *name_o = PyUnicode_InternFromString("negmeta");
    if (!name_o)
        return NULL;

    PyHeapTypeObject *ht = (PyHeapTypeObject *) PyType_GenericAlloc(&PyType_Type, 0);
    if (!ht) {
        Py_DECREF(name_o);
        return NULL;
    }

    ht->ht_name = name_o;
    ht->ht_qualname = Py_NewRef(name_o);
    ht->ht_module = NULL;

    PyTypeObject *tp = &ht->ht_type;
    tp->tp_name = PyUnicode_AsUTF8(name_o);
    tp->tp_basicsize = -extra;            /* base-relative, as in PyType_Spec */
    tp->tp_itemsize = 0;
    tp->tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HEAPTYPE;
    tp->tp_as_async = &ht->as_async;
    tp->tp_as_number = &ht->as_number;
    tp->tp_as_sequence = &ht->as_sequence;
    tp->tp_as_mapping = &ht->as_mapping;
    tp->tp_as_buffer = &ht->as_buffer;
    tp->tp_base = &PyType_Type;
    Py_INCREF(tp->tp_base);

    Py_ssize_t before = tp->tp_basicsize;
    Py_ssize_t expected = ALIGN_UP(PyType_Type.tp_basicsize) + ALIGN_UP(extra);

    if (PyType_Ready(tp) != 0) {
        Py_DECREF(tp);
        return NULL;
    }

    return Py_BuildValue("{s:n,s:n,s:n,s:n,s:N}",
                         "basicsize_before_ready", before,
                         "basicsize_after_ready", tp->tp_basicsize,
                         "base_basicsize", PyType_Type.tp_basicsize,
                         "expected", expected,
                         "meta", (PyObject *) tp);
}

/* write a pattern into the 'extra' bytes past PyType_Type.tp_basicsize of
   an instance of the metaclass and read it back; returns -1 on success */
static PyObject *
fill_check(PyObject *self, PyObject *args)
{
    PyObject *obj;
    int extra, i;
    if (!PyArg_ParseTuple(args, "Oi", &obj, &extra))
        return NULL;
    unsigned char *p = (unsigned char *) obj + PyType_Type.tp_basicsize;
    for (i = 0; i < extra; i++)
        p[i] = (unsigned char) (i * 7 + 1);
    for (i = 0; i < extra; i++)
        if (p[i] != (unsigned char) (i * 7 + 1))
            return PyLong_FromLong(i);
    return PyLong_FromLong(-1);
}

static PyMethodDef methods[] = {
    {"make_meta", make_meta, METH_VARARGS,
     "make_meta(extra) -> dict; builds a metaclass with tp_basicsize=-extra"},
    {"fill_check", fill_check, METH_VARARGS,
     "fill_check(obj, extra) -> -1 if the extra tail bytes are usable"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "negative_basicsize", NULL, -1, methods
};

PyMODINIT_FUNC
PyInit_negative_basicsize(void)
{
    return PyModule_Create(&moduledef);
}
