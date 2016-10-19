#include "Python.h"

typedef struct {
    PyObject_HEAD
    int foo;
} mytype_object;


static PyObject *
mytype_item(mytype_object *o, Py_ssize_t i)
{
    return PyInt_FromLong(i + 42);
}

static PyObject *
mytype_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    return type->tp_alloc(type, 0);
}

static PySequenceMethods mytype_as_sequence = {
    (lenfunc)0,                      /*sq_length*/
    (binaryfunc)0,                   /*sq_concat*/
    (ssizeargfunc)0,                 /*sq_repeat*/
    (ssizeargfunc)mytype_item,       /*sq_item*/
};

static PyTypeObject mytype_type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "test_module.test_mytype",   /*tp_name*/
    sizeof(mytype_object),       /*tp_size*/
    0,                       /*tp_itemsize*/
    /* methods */
    0,                       /*tp_dealloc*/
    0,                       /*tp_print*/
    0,                       /*tp_getattr*/
    0,                       /*tp_setattr*/
    0,                       /*tp_compare*/
    0,                       /*tp_repr*/
    0,                       /*tp_as_number*/
    &mytype_as_sequence,     /*tp_as_sequence*/
    0,                       /*tp_as_mapping*/
    0,                       /*tp_hash*/
    0,                       /*tp_call*/
    0,                       /*tp_str*/
    0,                       /*tp_getattro*/
    0,                       /*tp_setattro*/
    0,                       /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    0,                       /*tp_doc*/
    0,                       /*tp_traverse*/
    0,                       /*tp_clear*/
    0,                       /*tp_richcompare*/
    0,                       /*tp_weaklistoffset*/
    0,                       /*tp_iter*/
    0,                       /*tp_iternext*/
    0,                       /*tp_methods*/
    0,                       /*tp_members*/
    0,                       /*tp_getset*/
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    0,                                          /* tp_init */
    PyType_GenericAlloc,                        /* tp_alloc */
    mytype_new,                                 /* tp_new */
    PyObject_Del,                               /* tp_free */
};

/* List of functions exported by this module */

static PyMethodDef foo_functions[] = {
    {NULL,        NULL}    /* Sentinel */
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "injection",
    "Module Doc",
    -1,
    foo_functions,
    NULL,
    NULL,
    NULL,
    NULL,
};
#define INITERROR return NULL

/* Initialize this module. */
#ifdef __GNUC__
extern __attribute__((visibility("default")))
#else
extern __declspec(dllexport)
#endif

PyMODINIT_FUNC
PyInit_foo(void)

#else

#define INITERROR return

/* Initialize this module. */
#ifdef __GNUC__
extern __attribute__((visibility("default")))
#else
extern __declspec(dllexport)
#endif

PyMODINIT_FUNC
initinjection(void)
#endif
{
    PyObject *d;
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("injection", foo_functions);
#endif
    if (module == NULL)
        INITERROR;

    if (PyType_Ready(&mytype_type) < 0)
        INITERROR;
    PyModule_AddObject(module, "test_mytype", (PyObject *)&mytype_type);
#if PY_MAJOR_VERSION >=3
    return module;
#endif
}
