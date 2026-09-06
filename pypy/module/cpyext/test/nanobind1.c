#include <Python.h>
#include <structmember.h>

// ----------------------------------------------------
// Part 0: PEP 697 -- relative basicsize, Py_RELATIVE_OFFSET members,
// PyObject_GetTypeData, as used by nanobind under the limited API:
// a metaclass extending 'type' keeps per-type data past PyHeapTypeObject,
// and instances keep their data past the base's basicsize.
// ----------------------------------------------------

typedef struct {
    int value;
    double d;
} pep697_data;

static PyMemberDef pep697_members[] = {
    {"value", T_INT, offsetof(pep697_data, value), Py_RELATIVE_OFFSET, NULL},
    {"d", T_DOUBLE, offsetof(pep697_data, d), Py_RELATIVE_OFFSET, NULL},
    {NULL}
};

static PyType_Slot pep697_slots[] = {
    {Py_tp_members, pep697_members},
    {0, NULL}
};

static PyType_Spec pep697_spec = {
    .name = "nanobind1.pep697",
    .basicsize = -(int) sizeof(pep697_data),
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .slots = pep697_slots,
};

typedef struct {
    void *ptr;
    long tag;
} pep697_meta_data;

static PyType_Slot pep697_meta_slots[] = {
    {Py_tp_base, NULL}, /* &PyType_Type, filled in module init for MSVC */
    {0, NULL}
};

static PyType_Spec pep697_meta_spec = {
    .name = "nanobind1.pep697_meta",
    .basicsize = -(int) sizeof(pep697_meta_data),
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .slots = pep697_meta_slots,
};

static PyObject *pep697_type = NULL;
static PyObject *pep697_meta = NULL;

/* (offset of the type data in the instance, PyType_GetTypeDataSize,
    value, d) read through PyObject_GetTypeData */
static PyObject *pep697_info(PyObject *self, PyObject *obj) {
    PyTypeObject *cls = (PyTypeObject *) pep697_type;
    if (!PyObject_TypeCheck(obj, cls)) {
        PyErr_SetString(PyExc_TypeError, "not a pep697 instance");
        return NULL;
    }
    pep697_data *data = (pep697_data *) PyObject_GetTypeData(obj, cls);
    if (data == NULL)
        return NULL;
    return Py_BuildValue("nnid", (Py_ssize_t) ((char *) data - (char *) obj),
                         PyType_GetTypeDataSize(cls), data->value, data->d);
}

static PyObject *pep697_set(PyObject *self, PyObject *args) {
    PyObject *obj;
    int value;
    if (!PyArg_ParseTuple(args, "Oi", &obj, &value))
        return NULL;
    pep697_data *data = (pep697_data *) PyObject_GetTypeData(
        obj, (PyTypeObject *) pep697_type);
    if (data == NULL)
        return NULL;
    data->value = value;
    Py_RETURN_NONE;
}

/* (offset of the meta data in the type object, PyType_Type.tp_basicsize,
    PyType_GetTypeDataSize, tag) */
static PyObject *pep697_meta_info(PyObject *self, PyObject *tp) {
    PyTypeObject *meta = (PyTypeObject *) pep697_meta;
    if (!PyObject_TypeCheck(tp, meta)) {
        PyErr_SetString(PyExc_TypeError, "not a pep697_meta instance");
        return NULL;
    }
    pep697_meta_data *data = (pep697_meta_data *) PyObject_GetTypeData(tp, meta);
    if (data == NULL)
        return NULL;
    return Py_BuildValue("nnnl", (Py_ssize_t) ((char *) data - (char *) tp),
                         PyType_Type.tp_basicsize,
                         PyType_GetTypeDataSize(meta), data->tag);
}

static PyObject *pep697_meta_set(PyObject *self, PyObject *args) {
    PyObject *tp;
    long tag;
    if (!PyArg_ParseTuple(args, "Ol", &tp, &tag))
        return NULL;
    pep697_meta_data *data = (pep697_meta_data *) PyObject_GetTypeData(
        tp, (PyTypeObject *) pep697_meta);
    if (data == NULL)
        return NULL;
    data->tag = tag;
    data->ptr = (void *) tp;
    Py_RETURN_NONE;
}

#define PEP697_METHODS \
    { "pep697_info", (PyCFunction) pep697_info, METH_O, NULL }, \
    { "pep697_set", (PyCFunction) pep697_set, METH_VARARGS, NULL }, \
    { "pep697_meta_info", (PyCFunction) pep697_meta_info, METH_O, NULL }, \
    { "pep697_meta_set", (PyCFunction) pep697_meta_set, METH_VARARGS, NULL },

// ----------------------------------------------------
// Part 1: Reproducer of reference counting issue
// https://foss.heptapod.net/pypy/pypy/-/issues/3844
// ----------------------------------------------------

PyObject *heap_type_new(PyTypeObject *tp, PyObject *args,
                        PyObject *kwds) {

    PyObject *obj = PyObject_Malloc(sizeof(PyObject));
    memset(obj, 0, sizeof(PyObject));
    return PyObject_Init(obj, tp);
}

void heap_type_dealloc(PyObject *self) {
    PyTypeObject *tp = Py_TYPE(self);
    tp->tp_free(self);

#if PY_VERSION_HEX > 0x03080000
    Py_DECREF(tp);
#endif
}

static PyType_Slot heap_type_slots[] = {
    { Py_tp_new, heap_type_new },
    { Py_tp_dealloc, heap_type_dealloc },
    { 0, NULL }
};

static PyType_Spec heap_type_spec = {
    .name = "nanobind1.heap_type",
    .flags = Py_TPFLAGS_DEFAULT|Py_TPFLAGS_HEAPTYPE,
    .slots = heap_type_slots,
    .basicsize = (int) sizeof(PyObject),
    .itemsize = 0
};

#if PY_VERSION_HEX >= 0x03090000
// ----------------------------------------------------
// Part 2: Reproducer of vector call issue #1
// https://foss.heptapod.net/pypy/pypy/-/issues/3845
// ----------------------------------------------------

typedef struct {
    PyObject_HEAD
    PyObject* (*vectorcall)(PyObject *, PyObject * const*, size_t, PyObject *);
} callable;

PyObject* my_vectorcall(PyObject *self, PyObject * const* args, size_t nargs,
                        PyObject *kwnames) {
    return PyLong_FromLong(1234);
}

static struct PyMemberDef callable_members[] = {
    // Supported starting with Python 3.9
    { "__vectorcalloffset__", T_PYSSIZET,
      (Py_ssize_t) offsetof(callable, vectorcall), READONLY, NULL },
     { NULL, 0, 0, 0, NULL }
 };

int callable_init(PyObject *self, PyObject *args, PyObject *kwds) {
    ((callable *) self)->vectorcall = my_vectorcall;
    return 0;
}

static PyType_Slot callable_slots[] = {
    { Py_tp_init, (void *) callable_init },
    { Py_tp_members, (void *) callable_members },
    { Py_tp_call, (void *) PyVectorcall_Call },
    { 0, NULL }
};

static PyType_Spec callable_spec = {
    .name = "nanobind1.callable",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_VECTORCALL,
    .slots = callable_slots,
    .basicsize = (int) sizeof(callable),
    .itemsize = 0
};

// ----------------------------------------------------
// Part #3: Reproducer of vector call issue #2
// https://foss.heptapod.net/pypy/pypy/-/issues/3845
// ----------------------------------------------------

static PyObject* call(PyObject* self, PyObject* arg) {
    PyObject *value = PyLong_FromLong(1234);
    if (!value)
        return NULL;

    PyObject *args[2] = { NULL, value };
    size_t nargsf = 1 | PY_VECTORCALL_ARGUMENTS_OFFSET;

    PyObject *result = PyObject_Vectorcall(
        arg, args + 1, nargsf, NULL
    );

    Py_DECREF(value);

    return result;
}

struct PyMethodDef nanobind1_methods[] = {
    { "call", (PyCFunction) call, METH_O, NULL },
    PEP697_METHODS
    { NULL, NULL, 0, NULL},
};
#else
struct PyMethodDef nanobind1_methods[] = {
    PEP697_METHODS
    { NULL, NULL, 0, NULL},
};
#endif

// ----------------------------------------------------
// Part #4: Reproducer of extended type object issue
// https://foss.heptapod.net/pypy/pypy/-/issues/3847
// ----------------------------------------------------

typedef struct {
    PyHeapTypeObject ht;
    uint8_t extra[2048];
} ExtendedType;

int metaclass_init(PyObject *self, PyObject *args, PyObject *kwds) {
    int rv = PyType_Type.tp_init(self, args, kwds);
    // printf("Got to metaclass_init.\n");
    if (rv == 0)
        memset(((ExtendedType *) self)->extra, 0, 2048);
    return rv;
}

static PyType_Slot metaclass_slots[] = {
    { Py_tp_init, (void *) metaclass_init },
    { Py_tp_base, NULL }, /* filled in module init function */
    { 0, NULL }
};

static PyType_Spec metaclass_spec_bad = {
    .name = "nanobind1.metaclass_bad",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .slots = metaclass_slots,
    .itemsize = (int) sizeof(ExtendedType)
};

static PyType_Spec metaclass_spec_good = {
    .name = "nanobind1.metaclass_good",
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .slots = metaclass_slots,
    .basicsize = (int) sizeof(ExtendedType)
};

// ----------------------------------------------------

static PyModuleDef nanobind1_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "nanobind1",
    .m_doc = "Reproducer for miscellaneous PyPy issues",
    .m_size = -1,
    .m_methods = nanobind1_methods
};

PyMODINIT_FUNC
PyInit_nanobind1(void)
{
    /* done here for MSVC */
    metaclass_slots[1].pfunc =  &PyType_Type;

    PyObject *m = PyModule_Create(&nanobind1_module);
    if (m == NULL)
        return NULL;

    PyObject *heap_type = PyType_FromSpec(&heap_type_spec);

    if (!heap_type || PyModule_AddObject(m, "heap_type", heap_type) < 0) {
        Py_XDECREF(heap_type);
        Py_DECREF(m);
        return NULL;
    }

#if PY_VERSION_HEX >= 0x03090000
    PyObject *callable = PyType_FromSpec(&callable_spec);

    if (!callable || PyModule_AddObject(m, "callable", callable) < 0) {
        Py_XDECREF(callable);
        Py_DECREF(m);
        return NULL;
    }
#endif

    PyObject *metaclass_good = PyType_FromSpec(&metaclass_spec_good);

    if (!metaclass_good || PyModule_AddObject(m, "metaclass_good", metaclass_good) < 0) {
        Py_XDECREF(metaclass_good);
        Py_DECREF(m);
        return NULL;
    }

    PyObject *metaclass_bad = PyType_FromSpec(&metaclass_spec_bad);

    if (!metaclass_bad || PyModule_AddObject(m, "metaclass_bad", metaclass_bad) < 0) {
        Py_XDECREF(metaclass_bad);
        Py_DECREF(m);
        return NULL;
    }

    pep697_meta_slots[0].pfunc = &PyType_Type;
    pep697_meta = PyType_FromSpec(&pep697_meta_spec);
    if (!pep697_meta) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(pep697_meta);
    if (PyModule_AddObject(m, "pep697_meta", pep697_meta) < 0) {
        Py_DECREF(pep697_meta);
        Py_DECREF(m);
        return NULL;
    }

    pep697_type = PyType_FromMetaclass((PyTypeObject *) pep697_meta, NULL,
                                       &pep697_spec, NULL);
    if (!pep697_type) {
        Py_DECREF(m);
        return NULL;
    }
    Py_INCREF(pep697_type);
    if (PyModule_AddObject(m, "pep697", pep697_type) < 0) {
        Py_DECREF(pep697_type);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}

