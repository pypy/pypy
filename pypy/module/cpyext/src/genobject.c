#include "Python.h"

PyCodeObject *
PyGen_GetCode(PyGenObject *gen)
{
    PyObject *res = gen->gi_code;
    Py_XINCREF(res);
    return (PyCodeObject *)res;
}
