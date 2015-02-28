#include "Python.h"

static PyMethodDef date_functions[] = {
    {NULL, NULL}
};

PyMODINIT_FUNC
initdate(void)
{
    PyObject *module;
    Py_InitModule("date", date_functions);
    module = PyImport_ImportModule("apple.banana");
    Py_DECREF(module);
}
