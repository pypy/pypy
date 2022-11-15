#include <Python.h>
#include <structmember.h>

#define USE_VECTORCALL_METHOD (PY_VERSION_HEX >= 0x03090000)

// ----------------------------------------------------
// Part #1: Reproducer of cyclic GC issue
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
    PyList_Append(global_list, PyUnicode_FromString("wrapper tp_dealloc called."));
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
    .name = "nanobind2.wrapper",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .slots = wrapper_slots,
    .basicsize = (int) sizeof(wrapper),
    .itemsize = 0
};

// ----------------------------------------------------
// Part #2: Reproducer of name inconsistencies
// ----------------------------------------------------

static int func_init(PyObject *self, PyObject *args, PyObject *kwds) {
    return 0;
}

static PyObject *func_get_name(PyObject *self, void* unused) {
    return PyUnicode_FromString("my_name");
}

static PyObject *func_get_qualname(PyObject *self, void* unused) {
    return PyUnicode_FromString("my_qualname");
}

static PyObject *func_get_module(PyObject *self, void* unused) {
    return PyUnicode_FromString("my_module");
}

static PyGetSetDef func_getset[] = {
    { "__name__", func_get_name, NULL, NULL, NULL },
    { "__qualname__", func_get_qualname, NULL, NULL, NULL },
    { "__module__", func_get_module, NULL, NULL, NULL },
    { NULL, NULL, NULL, NULL, NULL }
};

static PyType_Slot func_slots[] = {
    { Py_tp_init, func_init },
    { Py_tp_getset, func_getset },
    { 0, NULL }
};

static PyType_Spec func_spec = {
    .name = "nanobind2.func",
    .flags = Py_TPFLAGS_DEFAULT,
    .slots = func_slots,
    .basicsize = (int) sizeof(PyObject),
    .itemsize = 0
};

#if USE_VECTORCALL_METHOD == 1
// ----------------------------------------------------
// Part #3: Reproducer of method vector call issue
// ----------------------------------------------------

static PyObject* method_call(PyObject* self, PyObject* arg) {
    PyObject *value = PyLong_FromLong(1234);
    if (!value)
        return NULL;

    PyObject *name = PyUnicode_FromString("my_method");
    if (!name) {
        Py_DECREF(value);
        return NULL;
    }

    PyObject *args[2] = { arg, value };
    size_t nargsf = 2 | PY_VECTORCALL_ARGUMENTS_OFFSET;

    PyObject *result = PyObject_VectorcallMethod(
        name, args, nargsf, NULL);

    Py_DECREF(value);
    Py_DECREF(name);

    return result;
}

static PyObject* method_call_kw(PyObject* self, PyObject* arg) {
    PyObject *value = NULL,
             *name = NULL,
             *kwnames = NULL,
             *kw_name = NULL,
             *kw_value = NULL,
             *result = NULL;

    value = PyLong_FromLong(1234);
    if (!value)
        goto leave;

    name = PyUnicode_FromString("my_method");
    if (!name)
        goto leave;

    kwnames = PyTuple_New(1);
    if (!kwnames)
        goto leave;

    kw_name = PyUnicode_InternFromString("foo");
    if (!kw_name)
        goto leave;
    PyTuple_SET_ITEM(kwnames, 0, kw_name);

    kw_value = PyUnicode_FromString("bar");
    if (!kw_value)
        goto leave;

    PyObject *args[3] = { arg, value, kw_value };
    size_t nargsf = 2 | PY_VECTORCALL_ARGUMENTS_OFFSET;

    result = PyObject_VectorcallMethod(
        name, args, nargsf, kwnames);

leave:
    Py_XDECREF(value);
    Py_XDECREF(name);
    Py_XDECREF(kwnames);
    Py_XDECREF(kw_value);

    return result;
}

struct PyMethodDef pypy_issues_methods[] = {
    { "method_call", (PyCFunction) method_call, METH_O, NULL },
    { "method_call_kw", (PyCFunction) method_call_kw, METH_O, NULL },
    { NULL, NULL, 0, NULL},
};
#endif

// ----------------------------------------------------

static PyModuleDef pypy_issues_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "nanobind2",
    .m_doc = "Reproducer for miscellaneous PyPy issues",
    .m_size = -1,
#if USE_VECTORCALL_METHOD == 1
    .m_methods = pypy_issues_methods
#endif
};

PyMODINIT_FUNC
PyInit_nanobind2(void)
{
    PyObject *m = PyModule_Create(&pypy_issues_module);
    if (m == NULL) {
        return NULL;
	}

	global_list = PyList_New(0);

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

    PyObject *func = PyType_FromSpec(&func_spec);

    if (!func || PyModule_AddObject(m, "func", func) < 0) {
        Py_XDECREF(func);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
