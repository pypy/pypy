#include "Python.h"

static PyMethodDef banana_functions[] = {
    {NULL, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "banana",
    "Module Doc",
    -1,
    &banana_functions
};

PyObject *PyInit_banana(void)
{
    return PyModule_Create(&moduledef);
}
