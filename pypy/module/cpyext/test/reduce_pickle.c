/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_methodobject.py's
 * test_reduce_pickle_module actually exercises: a module-level function
 * named like the __reduce__ helper Cython generates for cdef classes,
 * whose __module__ correctly names this module. See
 * cython/tests/run/reduce_pickle.pyx (Wrapper class) for the original.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
pyx_unpickle_Wrapper(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyMethodDef reduce_pickle_methods[] = {
    {"__pyx_unpickle_Wrapper", pyx_unpickle_Wrapper, METH_VARARGS, NULL},
    {NULL, NULL}
};

static struct PyModuleDef reduce_pickle_module = {
    PyModuleDef_HEAD_INIT,
    "reduce_pickle",
    NULL,
    -1,
    reduce_pickle_methods,
};

PyMODINIT_FUNC
PyInit_reduce_pickle(void)
{
    return PyModule_Create(&reduce_pickle_module);
}
