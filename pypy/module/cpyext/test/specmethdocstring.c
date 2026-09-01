/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_methodobject.py's
 * test_wrapper actually exercises: a class C whose __iter__/__next__ are
 * plain PyMethodDef entries (as Cython emits them, alongside filling the
 * tp_iter/tp_iternext slots) with real docstrings, one of them using the
 * Argument Clinic "name(args)\n--\n\ndoc" convention so __text_signature__
 * gets extracted from it. See cython/tests/compile/specmethdocstring.pyx.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
C_iter(PyObject *self, PyObject *Py_UNUSED(ignored))
{
    Py_RETURN_FALSE;
}

static PyObject *
C_next(PyObject *self, PyObject *Py_UNUSED(ignored))
{
    Py_RETURN_FALSE;
}

static PyMethodDef C_methods[] = {
    {"__iter__", C_iter, METH_NOARGS, "usable docstring"},
    {"__next__", C_next, METH_NOARGS, "__next__($self, /)\n--\n\nusable docstring"},
    {NULL, NULL}
};

static PyTypeObject C_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "specmethdocstring.C",
    .tp_basicsize = sizeof(PyObject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_methods = C_methods,
};

static struct PyModuleDef specmethdocstring_module = {
    PyModuleDef_HEAD_INIT,
    "specmethdocstring",
    NULL,
    -1,
};

PyMODINIT_FUNC
PyInit_specmethdocstring(void)
{
    PyObject *m;

    if (PyType_Ready(&C_Type) < 0)
        return NULL;

    m = PyModule_Create(&specmethdocstring_module);
    if (m == NULL)
        return NULL;

    Py_INCREF(&C_Type);
    if (PyModule_AddObject(m, "C", (PyObject *)&C_Type) < 0) {
        Py_DECREF(&C_Type);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}
