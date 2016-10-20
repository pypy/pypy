#include "Python.h"

typedef Py_intptr_t npy_intp;

typedef struct _PyArray_Descr  PyArray_Descr;

typedef struct tagPyArrayObject_fields {
    PyObject_HEAD
    /* Pointer to the raw data buffer */
    char *data;
    /* The number of dimensions, also called 'ndim' */
    int nd;
    /* The size in each dimension, also called 'shape' */
    npy_intp *dimensions;
    /*
     * Number of bytes to jump to get to the
     * next element in each dimension
     */
    npy_intp *strides;
    /*
     * This object is decref'd upon
     * deletion of array. Except in the
     * case of UPDATEIFCOPY which has
     * special handling.
     *
     * For views it points to the original
     * array, collapsed so no chains of
     * views occur.
     *
     * For creation from buffer object it
     * points to an object that should be
     * decref'd on deletion
     *
     * For UPDATEIFCOPY flag this is an
     * array to-be-updated upon deletion
     * of this one
     */
    PyObject *base;
    /* Pointer to type structure */
    PyArray_Descr *descr;
    /* Flags describing array -- see below */
    int flags;
    /* For weak references */
    PyObject *weakreflist;
} PyArrayObject;

static
void array_dealloc(PyArrayObject * self){
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static
PyTypeObject PyArray_Type = {
#if defined(NPY_PY3K)
    PyVarObject_HEAD_INIT(NULL, 0)
#else
    PyObject_HEAD_INIT(NULL)
    0,                                          /* ob_size */
#endif
    "numpy.ndarray",                            /* tp_name */
    sizeof(PyArrayObject),                      /* tp_basicsize */
    0,                                          /* tp_itemsize */
    /* methods */
    (destructor)array_dealloc,                  /* tp_dealloc */
    (printfunc)NULL,                            /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
#if defined(NPY_PY3K)
    0,                                          /* tp_reserved */
#else
    0,                                          /* tp_compare */
#endif
    (reprfunc)NULL,                       /* tp_repr */
    0,
    //&array_as_number,                           /* tp_as_number */
    0,
    //&array_as_sequence,                         /* tp_as_sequence */
    0,
    //&array_as_mapping,                          /* tp_as_mapping */
    /*
     * The tp_hash slot will be set PyObject_HashNotImplemented when the
     * module is loaded.
     */
    (hashfunc)0,                                /* tp_hash */
    (ternaryfunc)0,                             /* tp_call */
    0,
    //(reprfunc)array_str,                        /* tp_str */
    (getattrofunc)0,                            /* tp_getattro */
    (setattrofunc)0,                            /* tp_setattro */
    0,
    //&array_as_buffer,                           /* tp_as_buffer */
    (Py_TPFLAGS_DEFAULT
#if !defined(NPY_PY3K)
     | Py_TPFLAGS_CHECKTYPES
     | Py_TPFLAGS_HAVE_NEWBUFFER
#endif
     | Py_TPFLAGS_BASETYPE),                    /* tp_flags */
    0,                                          /* tp_doc */

    (traverseproc)0,                            /* tp_traverse */
    (inquiry)0,                                 /* tp_clear */
    0,
    //(richcmpfunc)array_richcompare,             /* tp_richcompare */
    offsetof(PyArrayObject, weakreflist), /* tp_weaklistoffset */
    0,
    //(getiterfunc)array_iter,                    /* tp_iter */
    (iternextfunc)0,                            /* tp_iternext */
    0,
    //array_methods,                              /* tp_methods */
    0,                                          /* tp_members */
    0,
    //array_getsetlist,                           /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)0,                                /* tp_init */
    0,
    //(allocfunc)array_alloc,                     /* tp_alloc */
    0,
    //(newfunc)array_new,                         /* tp_new */
    0,
    //(freefunc)array_free,                       /* tp_free */
    0,                                          /* tp_is_gc */
    0,                                          /* tp_bases */
    0,                                          /* tp_mro */
    0,                                          /* tp_cache */
    0,                                          /* tp_subclasses */
    0,                                          /* tp_weaklist */
    0,                                          /* tp_del */
    0,                                          /* tp_version_tag */
};

/* List of functions exported by this module */

static PyMethodDef multiarray_functions[] = {
    //{"make",      (PyCFunction)glob_make, METH_VARARGS, NULL},
    {NULL,        NULL}    /* Sentinel */
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "numpy.core.multiarray",
    "Module Doc",
    -1,
    multiarray_functions,
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
PyInit_multiarray(void)

#else

#define INITERROR return

/* Initialize this module. */
#ifdef __GNUC__
extern __attribute__((visibility("default")))
#else
extern __declspec(dllexport)
#endif

PyMODINIT_FUNC
initmultiarray(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("numpy.core.multiarray", multiarray_functions);
#endif
    if (module == NULL)
        INITERROR;

    if (PyType_Ready(&PyArray_Type) < 0)
        INITERROR;
    PyModule_AddObject(module, "ndarray", (PyObject *)&PyArray_Type);
#if PY_MAJOR_VERSION >=3
    return module;
#endif
}
