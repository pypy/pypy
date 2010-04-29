
/*
 * Trivial module which uses the PyMODINIT_FUNC macro.
 */

#include <Python.h>

static PyMethodDef methods[] = {
    { NULL }
};

PyMODINIT_FUNC
initmodinit(void) {
    Py_InitModule3("modinit", methods, "");
}

