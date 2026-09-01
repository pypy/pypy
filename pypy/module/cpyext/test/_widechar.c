// Enable asserts. This used to fail in that case only.
#undef NDEBUG

#include "Python.h"

static PyObject *
test_widechar(PyObject *self)
{
    PyObject *wide;

    wide = PyUnicode_New(1, 0x10ffff);
    if (wide == NULL)
        return NULL;
    if (PyUnicode_WriteChar(wide, 0, (Py_UCS4)0x110000u) < 0) {
        Py_DECREF(wide);
        return NULL;
    }
    return wide;
}

static PyObject *
get_sizeof_wchar(PyObject *self)
{
    return PyLong_FromLong(sizeof(wchar_t));
}

static PyMethodDef TestMethods[] = {
    {"test_widechar",    (PyCFunction)test_widechar,   METH_NOARGS},
    {"get_sizeof_wchar", (PyCFunction)get_sizeof_wchar,METH_NOARGS},
    {NULL, NULL} /* sentinel */
};

static struct PyModuleDef _testcapimodule = {
    PyModuleDef_HEAD_INIT,
    "_widechar",
    NULL,
    -1,
    NULL,
};

PyMODINIT_FUNC
PyInit__widechar(void)
{
    PyObject *m;
    m = PyModule_Create(&_testcapimodule);
    if (m == NULL)
        return NULL;
    PyModule_AddFunctions(m, TestMethods);
    return m;
}
