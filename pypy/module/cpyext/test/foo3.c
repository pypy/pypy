#include <Python.h>
#include <stdio.h>

PyObject* foo3type_tp_new(PyTypeObject* metatype, PyObject* args, PyObject* kwds)
{
    PyObject* newType;
    newType = PyType_Type.tp_new(metatype, args, kwds);
    return newType;
}

#define BASEFLAGS Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE

PyTypeObject footype = {
    PyVarObject_HEAD_INIT(NULL, 0)
    /*tp_name*/             "foo3.footype",
    /*tp_basicsize*/        sizeof(PyTypeObject),
    /*tp_itemsize*/         0,
    /*tp_dealloc*/          0,
    /*tp_print*/            0,
    /*tp_getattr*/          0,
    /*tp_setattr*/          0,
    /*tp_compare*/          0,
    /*tp_repr*/             0,
    /*tp_as_number*/        0,
    /*tp_as_sequence*/      0,
    /*tp_as_mapping*/       0,
    /*tp_hash*/             0,
    /*tp_call*/             0,
    /*tp_str*/              0,
    /*tp_getattro*/         0,
    /*tp_setattro*/         0,
    /*tp_as_buffer*/        0,
    /*tp_flags*/            BASEFLAGS,
    /*tp_doc*/              0,
    /*tp_traverse*/         0,
    /*tp_clear*/            0,
    /*tp_richcompare*/      0,
    /*tp_weaklistoffset*/   0,
    /*tp_iter*/             0,
    /*tp_iternext*/         0,
    /*tp_methods*/          0,
    /*tp_members*/          0,
    /*tp_getset*/           0,
    /*tp_base*/             0,  //  set to &PyType_Type in module init function (why can it not be done here?)
    /*tp_dict*/             0,
    /*tp_descr_get*/        0,
    /*tp_descr_set*/        0,
    /*tp_dictoffset*/       0,
    /*tp_init*/             0,
    /*tp_alloc*/            0,
    /*tp_new*/              foo3type_tp_new,
    /*tp_free*/             0,
    /*tp_is_gc*/            0,
    /*tp_bases*/            0,
    /*tp_mro*/              0,
    /*tp_cache*/            0,
    /*tp_subclasses*/       0,
    /*tp_weaklist*/         0
};

static PyMethodDef sbkMethods[] = {{NULL, NULL, 0, NULL}};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "foo",
    "Module Doc",
    -1,
    sbkMethods,
    NULL,
    NULL,
    NULL,
    NULL,
};

/* Initialize this module. */
#ifdef __GNUC__
extern __attribute__((visibility("default")))
#endif

PyMODINIT_FUNC
PyInit_foo3(void)
{
    PyObject *mod, *d;
    footype.tp_base = &PyType_Type;
    PyType_Ready(&footype);
    mod = PyModule_Create(&moduledef);
    if (mod == NULL)
        return NULL;
    d = PyModule_GetDict(mod);
    if (d == NULL)
        return NULL;
    if (PyDict_SetItemString(d, "footype", (PyObject *)&footype) < 0)
        return NULL;
    Py_INCREF(&footype);
    return mod;
}
