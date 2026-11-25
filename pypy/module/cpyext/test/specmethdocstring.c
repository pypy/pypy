/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_methodobject.py's
 * test_wrapper actually exercises: a class C whose __iter__/__next__ are
 * plain PyMethodDef entries (as Cython emits them, alongside filling the
 * tp_iter/tp_iternext slots) with real docstrings, one of them using the
 * Argument Clinic "name(args)\n--\n\ndoc" convention so __text_signature__
 * gets extracted from it, plus __len__, which only exists as a slot and so
 * gets its docstring through d_base.
 * See cython/tests/compile/specmethdocstring.pyx.
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

static Py_ssize_t
C_len(PyObject *self)
{
    return 0;
}

static PyMethodDef C_methods[] = {
    {"__iter__", C_iter, METH_NOARGS, "usable docstring"},
    {"__next__", C_next, METH_NOARGS, "__next__($self, /)\n--\n\nusable docstring"},
    {NULL, NULL}
};

static PyObject *
C_add(PyObject *self, PyObject *other)
{
    Py_RETURN_FALSE;
}

static PyObject *
C_getattro(PyObject *self, PyObject *name)
{
    return PyObject_GenericGetAttr(self, name);
}

static PySequenceMethods C_as_sequence = {
    .sq_length = C_len,
};

static PyNumberMethods C_as_number = {
    .nb_add = C_add,
};

static PyTypeObject C_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "specmethdocstring.C",
    .tp_basicsize = sizeof(PyObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = PyType_GenericNew,
    .tp_methods = C_methods,
    .tp_as_sequence = &C_as_sequence,
    .tp_as_number = &C_as_number,
    .tp_getattro = C_getattro,
};

/* D leaves its slots at 0.  Cython only copies a base's slot into a subclass
 * on PyPy versions whose PyType_Ready() does not inherit it, because copying
 * one shadows the base's descriptor. */
static PyTypeObject D_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "specmethdocstring.D",
    .tp_basicsize = sizeof(PyObject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
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

    /* A slot has no PyMethodDef to carry a docstring, so Cython repoints the
     * wrapper descriptor's d_base, then calls PyType_Modified() when it adds
     * __reduce_cython__ to the type dict. */
    {
        static const char *names[] = {"__len__", "__add__", "__getattr__"};
        static const char *docs[] = {"C.__len__ docstring",
                                     "C.__add__ docstring",
                                     "C.__getattr__ docstring"};
        static struct wrapperbase wb[3];
        int i;
        for (i = 0; i < 3; i++) {
            PyObject *w = PyObject_GetAttrString((PyObject *)&C_Type, names[i]);
            if (w == NULL)
                return NULL;
            if (!Py_IS_TYPE(w, &PyWrapperDescr_Type)) {
                Py_DECREF(w);
                PyErr_Format(PyExc_TypeError,
                             "%s is not a wrapper_descriptor", names[i]);
                return NULL;
            }
            wb[i] = *((PyWrapperDescrObject *)w)->d_base;
            wb[i].doc = docs[i];
            /* w is deliberately leaked, as Cython does: wb has to outlive it */
            ((PyWrapperDescrObject *)w)->d_base = &wb[i];
        }
        if (PyDict_SetItemString(C_Type.tp_dict, "extra", Py_None) < 0)
            return NULL;
        PyType_Modified(&C_Type);
    }

    D_Type.tp_base = &C_Type;
    if (PyType_Ready(&D_Type) < 0)
        return NULL;
    Py_INCREF(&D_Type);
    if (PyModule_AddObject(m, "D", (PyObject *)&D_Type) < 0) {
        Py_DECREF(&D_Type);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}
