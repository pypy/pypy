/* Built with Py_LIMITED_API to check that a cp312-abi3 extension loads and
   runs on PyPy.  See extra_tests/test_abi3_module.py. */
#define Py_LIMITED_API 0x030c0000
#include <Python.h>

static PyObject *
multiply(PyObject *self, PyObject *args)
{
    PyObject *in_a, *in_b, *result;
    Py_ssize_t i, len;

    if (!PyArg_ParseTuple(args, "OO", &in_a, &in_b)) {
        return NULL;
    }
    len = PySequence_Size(in_a);
    if (len < 0) {
        return NULL;
    }
    if (PySequence_Size(in_b) != len) {
        PyErr_SetString(PyExc_ValueError, "sequences of unequal length");
        return NULL;
    }
    result = PyList_New(len);
    if (result == NULL) {
        return NULL;
    }
    for (i = 0; i < len; i++) {
        PyObject *item, *prod;
        long a, b;

        item = PySequence_GetItem(in_a, i);
        if (item == NULL) {
            goto error;
        }
        a = PyLong_AsLong(item);
        Py_DECREF(item);
        if (a == -1 && PyErr_Occurred()) {
            goto error;
        }
        item = PySequence_GetItem(in_b, i);
        if (item == NULL) {
            goto error;
        }
        b = PyLong_AsLong(item);
        Py_DECREF(item);
        if (b == -1 && PyErr_Occurred()) {
            goto error;
        }
        prod = PyLong_FromLong(a * b);
        if (prod == NULL) {
            goto error;
        }
        if (PyList_SetItem(result, i, prod) < 0) {
            goto error;
        }
    }
    return result;

  error:
    Py_DECREF(result);
    return NULL;
}

static PyObject *
limited_api_version(PyObject *self, PyObject *noargs)
{
    return PyLong_FromLong(Py_LIMITED_API);
}

static PyMethodDef abi3_test_methods[] = {
    {"multiply", multiply, METH_VARARGS,
     "multiply(a, b) -> [x * y for x, y in zip(a, b)]"},
    {"limited_api_version", limited_api_version, METH_NOARGS,
     "the Py_LIMITED_API value this module was built with"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef abi3_test_module = {
    PyModuleDef_HEAD_INIT,
    "_abi3_test",
    "limited API test module",
    -1,
    abi3_test_methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit__abi3_test(void)
{
    return PyModule_Create(&abi3_test_module);
}
