#include "Python.h"

static PyMethodDef dotted_functions[] = {
    {NULL, NULL}
};

void initdotted(void)
{
    Py_InitModule("pypy.module.cpyext.test.dotted", dotted_functions);
}
