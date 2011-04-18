#include "Python.h"

typedef struct CmpObject {
    PyObject_HEAD
} CmpObject;


static PyObject* cmp_richcmp(PyObject *self, PyObject *other, int opid) {
    long val;
    if ((opid != Py_EQ && opid != Py_NE) || !PyInt_CheckExact(other)) {
        Py_INCREF(Py_NotImplemented);
        return Py_NotImplemented;
    }
    val = PyLong_AsLong(other);
    if (opid == Py_EQ) {
        return PyBool_FromLong(val == 3);
    }
    else if (opid == Py_NE) {
        return PyBool_FromLong(val != 3);
    }
    return Py_NotImplemented;
}

static long cmp_hashfunc(PyObject *self) {
    return 3;
}


PyTypeObject CmpType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "comparisons.CmpType",                          /* tp_name */
    sizeof(CmpObject),                              /* tp_basicsize */
    0,                                              /* tp_itemsize */
    0,                                              /* tp_dealloc */
    0,                                              /* tp_print */
    0,                                              /* tp_getattr */
    0,                                              /* tp_setattr */
    0,                                              /* tp_compare */
    0,                                              /* tp_repr */
    0,                                              /* tp_as_number */
    0,                                              /* tp_as_sequence */
    0,                                              /* tp_as_mapping */
    cmp_hashfunc,                                   /* tp_hash */
    0,                                              /* tp_call */
    0,                                              /* tp_str */
    0,                                              /* tp_getattro */
    0,                                              /* tp_setattro */
    0,                                              /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,         /* tp_flags */
    0,                                              /* tp_doc */
    (traverseproc)0,                                /* tp_traverse */
    0,                                              /* tp_clear */
    (richcmpfunc)cmp_richcmp,                       /* tp_richcompare */
    0,                                              /* tp_weaklistoffset */
    0,                                              /* tp_iter */
    0,                                              /* tp_iternext */
    0,                                              /* tp_methods */
    0,                                              /* tp_members */
    0,                                              /* tp_getset */
    0,                                              /* tp_base */
    0,                                              /* tp_dict */
    0,                                              /* tp_descr_get */
    0,                                              /* tp_descr_set */
    0,                                              /* tp_dictoffset */
    0,                                              /* tp_init */
    0,                                              /* tp_alloc */
    0,                                              /* tp_new */
    0                                               /* tp_free */
};


static int cmp_compare(PyObject *self, PyObject *other) {
    return -1;
}

PyTypeObject OldCmpType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "comparisons.OldCmpType",                       /* tp_name */
    sizeof(CmpObject),                              /* tp_basicsize */
    0,                                              /* tp_itemsize */
    0,                                              /* tp_dealloc */
    0,                                              /* tp_print */
    0,                                              /* tp_getattr */
    0,                                              /* tp_setattr */
    (cmpfunc)cmp_compare,                           /* tp_compare */
};


void initcomparisons(void)
{
    PyObject *m, *d;

    if (PyType_Ready(&CmpType) < 0)
        return;
    if (PyType_Ready(&OldCmpType) < 0)
        return;
    m = Py_InitModule("comparisons", NULL);
    if (m == NULL)
        return;
    d = PyModule_GetDict(m);
    if (d == NULL)
        return;
    if (PyDict_SetItemString(d, "CmpType", (PyObject *)&CmpType) < 0)
        return;
    if (PyDict_SetItemString(d, "OldCmpType", (PyObject *)&OldCmpType) < 0)
        return;
}
