
#define PY_SSIZE_T_CLEAN
#include <Python.h>

PyTypeObject POW_Type;

static PyObject *
new(PyTypeObject *type, PyObject *args, PyObject *keywds)
{
    return PyObject_New(PyObject, &POW_Type);
}
 
static PyObject *
power(PyObject *self, PyObject *other, PyObject *module)
{
    printf("called power\n");
    return PyLong_FromLong(123);
}

static PyNumberMethods pow_as_number = {
    .nb_power = power,
};

PyTypeObject POW_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "pow",
    .tp_new = new,
    .tp_as_number = &pow_as_number,
};

static struct PyModuleDef pow_module = {
    PyModuleDef_HEAD_INIT,
    "POW module",
    "Test module.",
    -1,
    NULL,
};

PyMODINIT_FUNC
PyInit_pow_mod(void)
{
    PyObject *m = PyModule_Create(&pow_module);
    if (PyModule_AddType(m, &POW_Type) < 0) {
        return NULL;
    }
    return m;
}
