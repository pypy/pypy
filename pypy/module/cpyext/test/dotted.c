#include "Python.h"

static PyMethodDef dotted_functions[] = {
    {NULL, NULL}
};

#ifdef __GNUC__
extern __attribute__((visibility("default")))
#else
extern __declspec(dllexport)
#endif

PyMODINIT_FUNC
initdotted(void)
{
    Py_InitModule("pypy.module.cpyext.test.dotted", dotted_functions);
}
