#include <Python.h>
#include <structmember.h>

// ----------------------------------------------------
// Reproducer of not calling wrapper_dealloc
// ----------------------------------------------------

typedef struct {
    PyObject_HEAD
    PyObject *nested;
} wrapper;

PyObject* global_list = NULL;

static int wrapper_init(PyObject *self, PyObject *args, PyObject *kwds) {
    PyList_Append(global_list, PyUnicode_FromString("wrapper tp_init called."));
    return 0;
}

static void wrapper_dealloc(PyObject *self) {
    PyList_Append(global_list, PyUnicode_FromString("wrapper tp_init called."));
    PyObject_GC_UnTrack(self);
    PyTypeObject *tp = Py_TYPE(self);
    Py_CLEAR(((wrapper *) self)->nested);
    tp->tp_free(self);
    Py_DECREF(tp);
}

static int wrapper_traverse(PyObject *self, visitproc visit, void *arg) {
    PyList_Append(global_list, PyUnicode_FromString("wrapper tp_traverse called."));
    Py_VISIT(((wrapper *) self)->nested);
    return 0;
}

static int wrapper_clear(PyObject *self) {
    PyList_Append(global_list, PyUnicode_FromString("wrapper tp_clear called."));
    Py_CLEAR(((wrapper *) self)->nested);
    return 0;
}

static PyMemberDef wrapper_members[] = {
    { "nested", T_OBJECT, offsetof(wrapper, nested), 0, NULL },
    { NULL , 0, 0, 0, NULL }
};

static PyType_Slot wrapper_slots[] = {
    { Py_tp_init, wrapper_init },
    { Py_tp_dealloc, wrapper_dealloc },
    { Py_tp_traverse, wrapper_traverse },
    { Py_tp_clear, wrapper_clear },
    { Py_tp_members, wrapper_members },
    { 0, NULL }
};

static PyType_Spec wrapper_spec = {
    .name = "pypy_issues.wrapper",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .slots = wrapper_slots,
    .basicsize = (int) sizeof(wrapper),
    .itemsize = 0
};

// ----------------------------------------------------

typedef struct {
    PyObject_HEAD
    PyObject* (*vectorcall)(PyObject *, PyObject * const*, size_t, PyObject *);
} callable;


PyObject* my_vectorcall(PyObject *self, PyObject * const* args, size_t nargs,
                        PyObject *kwnames) {
    PyErr_SetString(PyExc_TypeError, "oops, an exception!");
    return NULL;
}

static int callable_init(PyObject *self, PyObject *args, PyObject *kwds) {
    ((callable *) self)->vectorcall = my_vectorcall;
    return 0;
}

static struct PyMemberDef callable_members[] = {
    // Supported starting with Python 3.9
    { "__vectorcalloffset__", T_PYSSIZET,
      (Py_ssize_t) offsetof(callable, vectorcall), READONLY, NULL },
     { NULL, 0, 0, 0, NULL }
};

static PyType_Slot callable_slots[] = {
    { Py_tp_init, callable_init },
    { Py_tp_members, callable_members },
    { Py_tp_call, (void *) PyVectorcall_Call },
    { 0, NULL }
};

static PyType_Spec callable_spec = {
    .name = "pypy_issues.callable",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_VECTORCALL,
    .slots = callable_slots,
    .basicsize = (int) sizeof(callable),
    .itemsize = 0
};


// ----------------------------------------------------

static PyObject* get_name(PyObject* self, PyObject* arg) {
    if (PyType_CheckExact(arg)) {
        return PyUnicode_FromString(((PyTypeObject *) arg)->tp_name);
    } else {
        PyErr_SetString(PyExc_TypeError, "expected a type object");
        return NULL;
    }
}

// ----------------------------------------------------

struct PyMethodDef pypy_issues_methods[] = {
    { "get_name", (PyCFunction) get_name, METH_O, NULL },
    { NULL, NULL, 0, NULL},
};

// ----------------------------------------------------

static int dummy_init(PyObject *self, PyObject *args, PyObject *kwds) {
    printf("dummy tp_init called.\n");
    return 0;
}

static void dummy_dealloc(PyObject *self) {
    printf("dummy tp_dealloc called.\n");
    PyTypeObject *tp = Py_TYPE(self);
    tp->tp_free(self);
    Py_DECREF(tp);
}

static PyType_Slot dummy_slots[] = {
    { Py_tp_init, dummy_init },
    { Py_tp_dealloc, dummy_dealloc },
    { 0, NULL }
};

static PyType_Spec dummy_spec = {
    .name = "pypy_issues.dummy",
    .flags = Py_TPFLAGS_DEFAULT,
    .slots = dummy_slots,
    .basicsize = (int) sizeof(PyObject),
    .itemsize = 0
};

// ----------------------------------------------------

static PyModuleDef pypy_issues_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "pypy_issues",
    .m_doc = "Reproducer for miscellaneous PyPy issues",
    .m_size = -1,
    .m_methods = pypy_issues_methods
};

PyMODINIT_FUNC
PyInit_nanobind3(void)
{
	global_list = PyList_New(0);

    PyObject *m = PyModule_Create(&pypy_issues_module);
    if (m == NULL)
        return NULL;

    PyObject *wrapper = PyType_FromSpec(&wrapper_spec);

    if (!wrapper || PyModule_AddObject(m, "global_list", global_list) < 0) {
        Py_XDECREF(wrapper);
        Py_DECREF(m);
        return NULL;
    }

    if (!wrapper || PyModule_AddObject(m, "wrapper", wrapper) < 0) {
        Py_XDECREF(wrapper);
        Py_DECREF(m);
        return NULL;
    }

    PyObject *func = PyType_FromSpec(&callable_spec);

    if (!func || PyModule_AddObject(m, "callable", func) < 0) {
        Py_XDECREF(func);
        Py_DECREF(m);
        return NULL;
    }

    PyObject *dummy = PyType_FromSpec(&dummy_spec);

    if (!dummy || PyModule_AddObject(m, "dummy", dummy) < 0) {
        Py_XDECREF(dummy);
        Py_DECREF(m);
        return NULL;
    }

    PyObject *dummy_instance = PyObject_CallFunctionObjArgs(dummy, NULL);
    if (!dummy_instance || PyModule_AddObject(m, "dummy_instance", dummy_instance) < 0) {
        Py_XDECREF(dummy_instance);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
