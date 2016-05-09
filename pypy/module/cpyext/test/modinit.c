
/*
 * Trivial module which uses the PyMODINIT_FUNC macro.
 */

#include <Python.h>

static PyMethodDef methods[] = {
    { NULL }
};

#ifdef __GNUC__
extern __attribute__((visibility("default")))
#else
extern __declspec(dllexport)
#endif

PyMODINIT_FUNC
initmodinit(void) {
    Py_InitModule3("modinit", methods, "");
}

