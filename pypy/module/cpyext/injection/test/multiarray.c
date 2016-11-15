#include "Python.h"
#include "pymath.h"

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

typedef struct {
    PyObject_HEAD
    double value;
} PyDoubleScalarObject;

static PyTypeObject PyDoubleArrType_Type = {
#if defined(NPY_PY3K)
    PyVarObject_HEAD_INIT(NULL, 0)
#else
    PyObject_HEAD_INIT(NULL)
    0,                                          /* ob_size */
#endif
    "numpy.float64",                            /* tp_name*/
    sizeof(PyDoubleScalarObject),               /* tp_basicsize*/
    0,                                          /* tp_itemsize */
    0,                                          /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
#if defined(NPY_PY3K)
    0,                                          /* tp_reserved */
#else
    0,                                          /* tp_compare */
#endif
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    0,                                          /* tp_flags */
    0,                                          /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    0,                                          /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    &PyFloat_Type,                              /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    0,                                          /* tp_init */
    0,                                          /* tp_alloc */
    0,                                          /* tp_new */
    0,                                          /* tp_free */
    0,                                          /* tp_is_gc */
    0,                                          /* tp_bases */
    0,                                          /* tp_mro */
    0,                                          /* tp_cache */
    0,                                          /* tp_subclasses */
    0,                                          /* tp_weaklist */
    0,                                          /* tp_del */
    0,                                          /* tp_version_tag */
};

static
void array_dealloc(PyArrayObject * self){
    free(self->data);
    free(self->dimensions);
    free(self->strides);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static
PyObject * array_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds);

static int
array_assign_item(PyArrayObject *self, Py_ssize_t i, PyObject *op)
{
   if (i < 0 || i >= self->dimensions[0]) {
       PyErr_SetString(PyExc_IndexError, "index out of bounds");
       return -1;
   }

   double * data = (double*)self->data;
   double value = PyFloat_AsDouble(op);
   data[i] = value;

   return 0;
}

static PyObject *
array_item(PyArrayObject *self, Py_ssize_t i)
{
   if (i < 0 || i >= self->dimensions[0]) {
       PyErr_SetString(PyExc_IndexError, "index out of bounds");
       return NULL;
   }
   double * data = (double*)self->data;
   double value = data[i];
   if (i == 10) {
       // we try to modify this behaviour on the pypy level
       value += 42;
   }

   PyDoubleScalarObject *o = PyObject_New(PyDoubleScalarObject,
                                          &PyDoubleArrType_Type);
   o->value = value;
   return (PyObject *)o;
}

static
PySequenceMethods array_as_sequence = {
    (lenfunc)NULL,                  /*sq_length*/
    (binaryfunc)NULL,                       /*sq_concat is handled by nb_add*/
    (ssizeargfunc)NULL,
    (ssizeargfunc)array_item,
    (ssizessizeargfunc)NULL,
    (ssizeobjargproc)array_assign_item,        /*sq_ass_item*/
    (ssizessizeobjargproc)NULL,               /*sq_ass_slice*/
    (objobjproc) NULL,                         /*sq_contains */
    (binaryfunc) NULL,                      /*sg_inplace_concat */
    (ssizeargfunc)NULL,
};

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
    &array_as_sequence,                         /* tp_as_sequence */
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
    (newfunc)array_new,                         /* tp_new */
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

static PyObject *
array_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)
{
    Py_ssize_t size;
    if (!PyArg_ParseTuple(args, "n", &size)) {
        goto fail;
    }

    PyArrayObject * array = (PyArrayObject *)subtype->tp_alloc(subtype, 0);
    array->data = malloc(sizeof(double)*size);
    array->nd = 1;
    npy_intp * dims = malloc(sizeof(npy_intp)*1);
    dims[0] = size;
    array->dimensions = dims;
    npy_intp * strides = malloc(sizeof(npy_intp)*1);
    strides[0] = 0;
    array->strides = strides;
    array->base = NULL;
    array->descr = NULL;
    array->flags = 0;
    array->weakreflist = NULL;
    return (PyObject*)array;
fail:
    return NULL;
}

enum kOP {MULT, ADD, SUB, DIV};

static PyObject*
array_op(PyObject* obj1, PyObject* obj2, enum kOP op)
{
    int n1=-1, n2=-1, m, i1, i2, j;
    double *v1, *v2, *r, tmp1, tmp2;
    PyObject* ret = NULL, *tuple=NULL;
    if (obj1->ob_type == &PyArray_Type)
    {
        n1 = ((PyArrayObject*)obj1)->dimensions[0];
        v1 = (double*)((PyArrayObject*)obj1)->data;       
    }
    else
    {
        tmp1 = PyFloat_AsDouble(obj1);
        if (PyErr_Occurred())
            return NULL;
        v1 = &tmp1;
        n1 = 1;
    }
    if (obj2->ob_type == &PyArray_Type)
    {
        n2 = ((PyArrayObject*)obj2)->dimensions[0];
        v2 = (double*)((PyArrayObject*)obj2)->data;       
    }
    else
    {
        tmp2 = PyFloat_AsDouble(obj2);
        if (PyErr_Occurred())
            return NULL;
        v2 = &tmp2;
        n2 = 1;
    }
    if ( !(n1 == n2 || n1 == 1 || n2 == 1))
    {
        PyErr_SetString(PyExc_ValueError, "dimension mismatch");
        return NULL;
    }
    m = n1 > n2? n1 : n2;
    tuple = PyTuple_New(1);
    PyTuple_SetItem(tuple, 0, PyInt_FromLong(m));
    ret = array_new(&PyArray_Type, tuple, NULL);
    Py_DECREF(tuple);
    r = (double*)((PyArrayObject*)ret)->data;
    for (i1=0, i2=0, j=0; j < m; j++, i1++, i2++)
    {
        if (i1 >= n1) i1 = 0;
        if (i2 >= n2) i2 = 0;
        switch (op)
        {
            case MULT:
                r[j] = v1[i1] * v2[i2] + 3;
                break;
            case ADD:
                r[j] = v1[i1] + v2[i2] + 3;
                break;
            case SUB:
                r[j] = v1[i1] - v2[i2] + 3;
                break;
            case DIV:
                if (v2[i2] == 0)
                    r[j] = Py_NAN;
                else
                    r[j] = v1[i1] / v2[i2] + 3;
                break;
        }
    } 
    return ret;
}

static PyObject*
array_multiply(PyObject* obj1, PyObject* obj2)
{
    return array_op(obj1, obj2, MULT);
}

static PyObject*
array_add(PyObject* obj1, PyObject* obj2)
{
    return array_op(obj1, obj2, ADD);
}

static PyObject*
array_sub(PyObject* obj1, PyObject* obj2)
{
    return array_op(obj1, obj2, SUB);
}

static PyObject*
array_divide(PyObject* obj1, PyObject* obj2)
{
    return array_op(obj1, obj2, DIV);
}

static PyNumberMethods array_as_number = {
    (binaryfunc)array_add, /* nb_add*/
    (binaryfunc)array_sub, /* nb_subtract */
    (binaryfunc)array_multiply, /* nb_multiply */
    (binaryfunc)array_divide, /* nb_divide */
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
    PyObject *infodict, *s;
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("numpy.core.multiarray", multiarray_functions);
#endif
    if (module == NULL)
        INITERROR;

    PyArray_Type.tp_as_number = &array_as_number;
    
    if (PyType_Ready(&PyArray_Type) < 0)
        INITERROR;
    PyModule_AddObject(module, "ndarray", (PyObject *)&PyArray_Type);

    if (PyType_Ready(&PyDoubleArrType_Type) < 0)
        INITERROR;
    infodict = PyDict_New();

    PyDict_SetItemString(infodict, "DOUBLE",
#if defined(NPY_PY3K)
            s = Py_BuildValue("CiiiO", whatever,
#else
            s = Py_BuildValue("ciiiO", 'd',
#endif
                12,
                64,
                8,
                (PyObject *) &PyDoubleArrType_Type));
    Py_DECREF(s);

    PyModule_AddObject(module, "typeinfo", infodict);

#if PY_MAJOR_VERSION >=3
    return module;
#endif
}

PyMODINIT_FUNC
initmultiarray_PLAIN(void)
{
    PyArray_Type.tp_name = "ndarray_dont_patch_me_please";
    initmultiarray();
}
