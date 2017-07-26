#include "Python.h"

static PyMethodDef banana_functions[] = {
    {NULL, NULL}
};

#ifdef __GNUC__
extern __attribute__((visibility("default")))
#else
extern __declspec(dllexport)
#endif

PyMODINIT_FUNC
initbanana(void)
{
    Py_InitModule("banana", banana_functions);
}
