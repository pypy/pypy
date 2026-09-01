/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_genobject.py actually
 * exercises: a custom iterator type whose tp_dealloc unconditionally calls
 * PyObject_ClearWeakRefs(self), matching CPython 3.12+ Cython generator
 * codegen, plus any_in_conditional_gen() (see cython/tests/run/any.pyx)
 * built on top of it so a short-circuiting any() abandons it mid-iteration.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

typedef struct {
    PyObject_HEAD
    PyObject *items;
    Py_ssize_t pos;
    PyObject *weakreflist;
} genexprIterObject;

static void
genexpr_iter_dealloc(genexprIterObject *self)
{
    PyObject_ClearWeakRefs((PyObject *)self);
    Py_DECREF(self->items);
    PyObject_Del(self);
}

static PyObject *
genexpr_iter_self(PyObject *self)
{
    Py_INCREF(self);
    return self;
}

static PyObject *
genexpr_iter_next(genexprIterObject *self)
{
    if (self->pos >= PyList_GET_SIZE(self->items)) {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    PyObject *item = PyList_GET_ITEM(self->items, self->pos);
    self->pos++;
    Py_INCREF(item);
    return item;
}

static PyTypeObject genexprIter_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "any.genexpr_iter",
    .tp_basicsize = sizeof(genexprIterObject),
    .tp_dealloc = (destructor)genexpr_iter_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_weaklistoffset = offsetof(genexprIterObject, weakreflist),
    .tp_iter = genexpr_iter_self,
    .tp_iternext = (iternextfunc)genexpr_iter_next,
};

/* any(x % 3 for x in seq if x % 2 == 1) */
static PyObject *
any_in_conditional_gen(PyObject *self, PyObject *seq)
{
    PyObject *iter = PyObject_GetIter(seq);
    if (iter == NULL)
        return NULL;

    PyObject *items = PyList_New(0);
    if (items == NULL) {
        Py_DECREF(iter);
        return NULL;
    }

    PyObject *item;
    while ((item = PyIter_Next(iter)) != NULL) {
        long v = PyLong_AsLong(item);
        Py_DECREF(item);
        if (v == -1 && PyErr_Occurred())
            goto error;
        if (v % 2 != 0) {
            PyObject *pv = PyLong_FromLong(v % 3);
            if (pv == NULL || PyList_Append(items, pv) < 0) {
                Py_XDECREF(pv);
                goto error;
            }
            Py_DECREF(pv);
        }
    }
    Py_DECREF(iter);
    if (PyErr_Occurred()) {
        Py_DECREF(items);
        return NULL;
    }

    genexprIterObject *gen = PyObject_New(genexprIterObject, &genexprIter_Type);
    if (gen == NULL) {
        Py_DECREF(items);
        return NULL;
    }
    gen->items = items;  /* steals reference */
    gen->pos = 0;
    gen->weakreflist = NULL;

    PyObject *builtins = PyImport_ImportModule("builtins");
    if (builtins == NULL) {
        Py_DECREF(gen);
        return NULL;
    }
    PyObject *any_func = PyObject_GetAttrString(builtins, "any");
    Py_DECREF(builtins);
    if (any_func == NULL) {
        Py_DECREF(gen);
        return NULL;
    }
    PyObject *result = PyObject_CallFunctionObjArgs(any_func, (PyObject *)gen, NULL);
    Py_DECREF(any_func);
    /* If any() short-circuited, this is the last reference: it triggers
       genexpr_iter_dealloc() right here, mid-iteration. */
    Py_DECREF(gen);
    return result;

error:
    Py_DECREF(iter);
    Py_DECREF(items);
    return NULL;
}

static PyMethodDef any_methods[] = {
    {"any_in_conditional_gen", any_in_conditional_gen, METH_O, NULL},
    {NULL, NULL}
};

static struct PyModuleDef any_module = {
    PyModuleDef_HEAD_INIT,
    "any",
    NULL,
    -1,
    any_methods,
};

PyMODINIT_FUNC
PyInit_any(void)
{
    if (PyType_Ready(&genexprIter_Type) < 0)
        return NULL;
    return PyModule_Create(&any_module);
}
