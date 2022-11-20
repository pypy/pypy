#include <Python.h>
#include <structmember.h>

// ----------------------------------------------
// Reproducer of not calling dealloc when raising
// ----------------------------------------------

typedef struct {
    PyObject_HEAD
    PyObject* (*vectorcall)(PyObject *, PyObject * const*, size_t, PyObject *);
} callable;

typedef struct {
    PyObject_HEAD
    PyObject* (*vectorcall)(PyObject *, PyObject * const*, size_t, PyObject *);
} callable_raises;

PyObject* global_list = NULL;

PyObject* vectorcall_raises(PyObject *self, PyObject * const* args, size_t nargs,
                        PyObject *kwnames) {
    PyErr_SetString(PyExc_TypeError, "oops, an exception!");
    return NULL;
}

PyObject* my_vectorcall(PyObject *self, PyObject * const* args, size_t nargs,
                        PyObject *kwnames) {
    return PyLong_FromLong(1234);
}

static int callable_init(PyObject *self, PyObject *args, PyObject *kwds) {
    PyList_Append(global_list, PyUnicode_FromString("callable tp_init called."));
    ((callable *) self)->vectorcall = my_vectorcall;
    return 0;
}

static int callable_raises_init(PyObject *self, PyObject *args, PyObject *kwds) {
    PyList_Append(global_list, PyUnicode_FromString("callable_raises tp_init called."));
    ((callable_raises *) self)->vectorcall = vectorcall_raises;
    return 0;
}

static void callable_dealloc(PyObject *self) {
    PyList_Append(global_list, PyUnicode_FromString("callable tp_dealloc called."));
    PyTypeObject *tp = Py_TYPE(self);
    tp->tp_free(self);
    Py_DECREF(tp);
}

static void callable_raises_dealloc(PyObject *self) {
    PyList_Append(global_list, PyUnicode_FromString("callable_raises tp_dealloc called."));
    PyTypeObject *tp = Py_TYPE(self);
    tp->tp_free(self);
    Py_DECREF(tp);
}


static struct PyMemberDef callable_members[] = {
    // Supported starting with Python 3.9
    { "__vectorcalloffset__", T_PYSSIZET,
      (Py_ssize_t) offsetof(callable, vectorcall), READONLY, NULL },
     { NULL, 0, 0, 0, NULL }
};

static struct PyMemberDef callable_raises_members[] = {
    // Supported starting with Python 3.9
    { "__vectorcalloffset__", T_PYSSIZET,
      (Py_ssize_t) offsetof(callable_raises, vectorcall), READONLY, NULL },
     { NULL, 0, 0, 0, NULL }
};

static PyType_Slot callable_slots[] = {
    { Py_tp_init, callable_init },
    { Py_tp_members, callable_members },
    { Py_tp_dealloc, callable_dealloc },
    { Py_tp_call, (void *) PyVectorcall_Call },
    { 0, NULL }
};

static PyType_Slot callable_raises_slots[] = {
    { Py_tp_init, callable_raises_init },
    { Py_tp_members, callable_raises_members },
    { Py_tp_dealloc, callable_raises_dealloc },
    { Py_tp_call, (void *) PyVectorcall_Call },
    { 0, NULL }
};

static PyType_Spec callable_spec = {
    .name = "nanobind3.callable",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_VECTORCALL,
    .slots = callable_slots,
    .basicsize = (int) sizeof(callable),
    .itemsize = 0
};

static PyType_Spec callable_raises_spec = {
    .name = "nanobind3.callable_raises",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_VECTORCALL,
    .slots = callable_raises_slots,
    .basicsize = (int) sizeof(callable_raises),
    .itemsize = 0
};


// ----------------------------------------------------

static PyModuleDef pypy_issues_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "nanobind3",
    .m_doc = "Reproducer for issue 3854",
    .m_size = -1,
};

PyMODINIT_FUNC
PyInit_nanobind3(void)
{
	global_list = PyList_New(0);

    PyObject *m = PyModule_Create(&pypy_issues_module);
    if (m == NULL)
        return NULL;

    PyObject *func = PyType_FromSpec(&callable_spec);

    if (!func || PyModule_AddObject(m, "global_list", global_list) < 0) {
        Py_XDECREF(func);
        Py_DECREF(m);
        return NULL;
    }

    if (!func || PyModule_AddObject(m, "callable", func) < 0) {
        Py_XDECREF(func);
        Py_DECREF(m);
        return NULL;
    }

    PyObject *func2 = PyType_FromSpec(&callable_raises_spec);

    if (!func2 || PyModule_AddObject(m, "callable_raises", func2) < 0) {
        Py_XDECREF(func);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
