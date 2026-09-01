/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_methodobject.py's
 * test_min_max actually exercises: max() called on mixtures of plain
 * Python ints, matching cython/tests/run/builtin_min_max.pyx (test_max2).
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static int
check_max(PyObject *max_func, PyObject *a, PyObject *b, long expected)
{
    PyObject *result = PyObject_CallFunctionObjArgs(max_func, a, b, NULL);
    if (result == NULL)
        return -1;
    long got = PyLong_AsLong(result);
    Py_DECREF(result);
    if (got == -1 && PyErr_Occurred())
        return -1;
    if (got != expected) {
        PyErr_Format(PyExc_AssertionError,
            "max() returned %ld, expected %ld", got, expected);
        return -1;
    }
    return 0;
}

static PyObject *
test_max2(PyObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *one = PyLong_FromLong(1);
    PyObject *two = PyLong_FromLong(2);
    PyObject *list = Py_BuildValue("[iii]", 1, 2, 3);
    PyObject *three = list ? PyLong_FromSsize_t(PyObject_Size(list)) : NULL;
    PyObject *builtins = PyImport_ImportModule("builtins");
    PyObject *max_func = builtins ? PyObject_GetAttrString(builtins, "max") : NULL;
    Py_XDECREF(builtins);

    if (one == NULL || two == NULL || three == NULL || max_func == NULL)
        goto error;

    if (check_max(max_func, one, two, 2) < 0) goto error;
    if (check_max(max_func, two, one, 2) < 0) goto error;
    if (check_max(max_func, one, three, 3) < 0) goto error;
    if (check_max(max_func, three, one, 3) < 0) goto error;

    Py_DECREF(one);
    Py_DECREF(two);
    Py_DECREF(three);
    Py_DECREF(list);
    Py_DECREF(max_func);
    Py_RETURN_NONE;

error:
    Py_XDECREF(one);
    Py_XDECREF(two);
    Py_XDECREF(three);
    Py_XDECREF(list);
    Py_XDECREF(max_func);
    return NULL;
}

static PyMethodDef builtin_min_max_methods[] = {
    {"test_max2", test_max2, METH_NOARGS, NULL},
    {NULL, NULL}
};

static struct PyModuleDef builtin_min_max_module = {
    PyModuleDef_HEAD_INIT,
    "builtin_min_max",
    NULL,
    -1,
    builtin_min_max_methods,
};

PyMODINIT_FUNC
PyInit_builtin_min_max(void)
{
    return PyModule_Create(&builtin_min_max_module);
}
