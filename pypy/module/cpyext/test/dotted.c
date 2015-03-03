#include "Python.h"

static PyMethodDef dotted_functions[] = {
    {NULL, NULL}
};

PyMODINIT_FUNC
initdotted(void)
{
    Py_InitModule("pypy.module.cpyext.test.dotted", dotted_functions);
}
