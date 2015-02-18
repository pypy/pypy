#include "Python.h"

static PyMethodDef banana_functions[] = {
    {NULL, NULL}
};

PyMODINIT_FUNC
initbanana(void)
{
    Py_InitModule("banana", banana_functions);
}
