/* An extension built against the limited API.
 *
 * Nothing here is interesting in itself: the point is that it must compile
 * and link with Py_LIMITED_API defined, using only what CPython exposes
 * under that macro.  If a header hides too much, this file stops compiling.
 */

#define Py_LIMITED_API 0x030C0000
#include "Python.h"
#include <stddef.h>     /* offsetof: CPython's limited Python.h does not */

static PyObject *
sizes(PyObject *self, PyObject *args)
{
    PyObject *list, *tuple, *item;
    Py_ssize_t n;

    list = PyList_New(2);
    if (list == NULL)
        return NULL;
    if (PyList_SetItem(list, 0, PyLong_FromLong(10)) < 0)
        goto error;
    if (PyList_SetItem(list, 1, PyLong_FromLong(20)) < 0)
        goto error;
    n = Py_SIZE(list);                  /* inline struct read, limited API */
    if (n != PyList_Size(list)) {
        PyErr_SetString(PyExc_AssertionError, "Py_SIZE(list) != PyList_Size");
        goto error;
    }
    tuple = PyTuple_New(1);
    if (tuple == NULL)
        goto error;
    if (PyTuple_SetItem(tuple, 0, list) < 0) {   /* steals list */
        Py_DECREF(tuple);
        return NULL;
    }
    item = PyTuple_GetItem(tuple, 0);
    if (item == NULL || Py_TYPE(item) != Py_TYPE(list)) {
        Py_DECREF(tuple);
        PyErr_SetString(PyExc_AssertionError, "bad item type");
        return NULL;
    }
    Py_DECREF(tuple);
    return PyLong_FromSsize_t(n);
error:
    Py_DECREF(list);
    return NULL;
}

static PyObject *
strings(PyObject *self, PyObject *args)
{
    PyObject *b, *u, *d;
    Py_ssize_t n;

    b = PyBytes_FromStringAndSize("abcd", 4);
    if (b == NULL)
        return NULL;
    n = Py_SIZE(b);                     /* bytes is a PyVarObject */
    u = PyUnicode_FromString("hello");
    if (u == NULL) {
        Py_DECREF(b);
        return NULL;
    }
    d = PyDict_New();
    if (d == NULL || PyDict_SetItemString(d, "b", b) < 0 ||
            PyDict_SetItemString(d, "u", u) < 0) {
        Py_XDECREF(d);
        Py_DECREF(b);
        Py_DECREF(u);
        return NULL;
    }
    Py_DECREF(b);
    Py_DECREF(u);
    if (n != 4 || PyDict_Size(d) != 2) {
        Py_DECREF(d);
        PyErr_SetString(PyExc_AssertionError, "bad sizes");
        return NULL;
    }
    return d;
}

static PyObject *
bytearray_size(PyObject *self, PyObject *arg)
{
    if (!PyByteArray_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "need a bytearray");
        return NULL;
    }
    return PyLong_FromSsize_t(Py_SIZE(arg));
}

/* A heap type from a spec.  This is the other half of the check: the names
 * used here must stay visible under Py_LIMITED_API.
 */
typedef struct {
    PyObject_HEAD
    long value;
} PointObject;

static PyObject *
point_doubled(PyObject *self, void *closure)
{
    return PyLong_FromLong(((PointObject *)self)->value * 2);
}

static int
point_set_doubled(PyObject *self, PyObject *arg, void *closure)
{
    long v = PyLong_AsLong(arg);
    if (v == -1 && PyErr_Occurred())
        return -1;
    ((PointObject *)self)->value = v / 2;
    return 0;
}

static int
point_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    long v = 0;
    if (!PyArg_ParseTuple(args, "|l", &v))
        return -1;
    ((PointObject *)self)->value = v;
    return 0;
}

static PyMemberDef point_members[] = {
    {"value", Py_T_LONG, offsetof(PointObject, value), 0, NULL},
    {"frozen", Py_T_LONG, offsetof(PointObject, value), Py_READONLY, NULL},
    {NULL, 0, 0, 0, NULL}
};

static PyGetSetDef point_getset[] = {
    {"doubled", point_doubled, point_set_doubled, NULL, NULL},
    {NULL, NULL, NULL, NULL, NULL}
};

static PyType_Slot point_slots[] = {
    {Py_tp_init, point_init},
    {Py_tp_members, point_members},
    {Py_tp_getset, point_getset},
    {0, NULL}
};

static PyType_Spec point_spec = {
    "limitedapi.Point",
    sizeof(PointObject),
    0,
    Py_TPFLAGS_DEFAULT,
    point_slots
};

static PyMethodDef methods[] = {
    {"sizes", sizes, METH_NOARGS, NULL},
    {"strings", strings, METH_NOARGS, NULL},
    {"bytearray_size", bytearray_size, METH_O, NULL},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "limitedapi", NULL, -1, methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_limitedapi(void)
{
    PyObject *mod, *point;

    mod = PyModule_Create(&moduledef);
    if (mod == NULL)
        return NULL;
    point = PyType_FromSpec(&point_spec);
    if (point == NULL) {
        Py_DECREF(mod);
        return NULL;
    }
    if (PyModule_AddObject(mod, "Point", point) < 0) {
        Py_DECREF(point);
        Py_DECREF(mod);
        return NULL;
    }
    return mod;
}
