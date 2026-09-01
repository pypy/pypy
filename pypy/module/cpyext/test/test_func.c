/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_methodobject.py's
 * test_module_name actually exercises: a module-level function whose
 * __module__ correctly names this module (issue 3993).
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
f(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyMethodDef test_func_methods[] = {
    {"f", f, METH_NOARGS, NULL},
    {NULL, NULL}
};

static struct PyModuleDef test_func_module = {
    PyModuleDef_HEAD_INIT,
    "test_func",
    NULL,
    -1,
    test_func_methods,
};

PyMODINIT_FUNC
PyInit_test_func(void)
{
    return PyModule_Create(&test_func_module);
}
