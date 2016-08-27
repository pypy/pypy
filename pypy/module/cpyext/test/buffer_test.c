#ifdef _MSC_VER
#define _CRT_SECURE_NO_WARNINGS 1
#endif
#include <Python.h>
#include <stdlib.h>
#include <stdio.h>

/* 
 * Adapted from https://jakevdp.github.io/blog/2014/05/05/introduction-to-the-python-buffer-protocol,
 * which is copyright Jake Vanderplas and released under the BSD license
 */

/* Structure defines a 1-dimensional strided array */
typedef struct{
    int* arr;
    Py_ssize_t length;
} MyArray;

/* initialize the array with integers 0...length */
void initialize_MyArray(MyArray* a, long length){
    int i;
    a->length = length;
    a->arr = (int*)malloc(length * sizeof(int));
    for(i=0; i<length; i++){
        a->arr[i] = i;
    }
}

/* free the memory when finished */
void deallocate_MyArray(MyArray* a){
    free(a->arr);
    a->arr = NULL;
}

/* tools to print the array */
char* stringify(MyArray* a, int nmax){
    char* output = (char*) malloc(nmax * 20);
    int k, pos = sprintf(&output[0], "[");

    for (k=0; k < a->length && k < nmax; k++){
        pos += sprintf(&output[pos], " %d", a->arr[k]);
    }
    if(a->length > nmax)
        pos += sprintf(&output[pos], "...");
    sprintf(&output[pos], " ]");
    return output;
}

void print_MyArray(MyArray* a, int nmax){
    char* s = stringify(a, nmax);
    printf("%s", s);
    free(s);
}

/* This is where we define the PyMyArray object structure */
typedef struct {
    PyObject_HEAD
    /* Type-specific fields go below. */
    MyArray arr;
} PyMyArray;


/* This is the __init__ function, implemented in C */
static int
PyMyArray_init(PyMyArray *self, PyObject *args, PyObject *kwds)
{
    int length = 0;
    static char *kwlist[] = {"length", NULL};
    // init may have already been called
    if (self->arr.arr != NULL) {
        deallocate_MyArray(&self->arr);
    }

    if (! PyArg_ParseTupleAndKeywords(args, kwds, "|i", kwlist, &length))
        return -1;

    if (length < 0)
        length = 0;

    initialize_MyArray(&self->arr, length);

    return 0;
}


/* this function is called when the object is deallocated */
static void
PyMyArray_dealloc(PyMyArray* self)
{
    deallocate_MyArray(&self->arr);
    Py_TYPE(self)->tp_free((PyObject*)self);
}


/* This function returns the string representation of our object */
static PyObject *
PyMyArray_str(PyMyArray * self)
{
  char* s = stringify(&self->arr, 10);
  PyObject* ret = PyUnicode_FromString(s);
  free(s);
  return ret;
}

/* Here is the buffer interface function */
static int
PyMyArray_getbuffer(PyObject *obj, Py_buffer *view, int flags)
{
  PyMyArray* self = (PyMyArray*)obj;
  fprintf(stdout, "in PyMyArray_getbuffer\n");
  if (view == NULL) {
    fprintf(stdout, "view is NULL\n");
    PyErr_SetString(PyExc_ValueError, "NULL view in getbuffer");
    return -1;
  }
  if (flags == 0) {
    fprintf(stdout, "flags is 0\n");
    PyErr_SetString(PyExc_ValueError, "flags == 0 in getbuffer");
    return -1;
  }

  view->obj = (PyObject*)self;
  view->buf = (void*)self->arr.arr;
  view->len = self->arr.length * sizeof(int);
  view->readonly = 0;
  view->itemsize = sizeof(int);
  view->format = "i";  // integer
  view->ndim = 1;
  view->shape = &self->arr.length;  // length-1 sequence of dimensions
  view->strides = &view->itemsize;  // for the simple case we can do this
  view->suboffsets = NULL;
  view->internal = NULL;

  Py_INCREF(self);  // need to increase the reference count
  return 0;
}

static PyBufferProcs PyMyArray_as_buffer = {
#if PY_MAJOR_VERSION < 3
  (readbufferproc)0,
  (writebufferproc)0,
  (segcountproc)0,
  (charbufferproc)0,
#endif
  (getbufferproc)PyMyArray_getbuffer,
  (releasebufferproc)0,  // we do not require any special release function
};


/* Here is the type structure: we put the above functions in the appropriate place
   in order to actually define the Python object type */
static PyTypeObject PyMyArrayType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pymyarray.PyMyArray",        /* tp_name */
    sizeof(PyMyArray),            /* tp_basicsize */
    0,                            /* tp_itemsize */
    (destructor)PyMyArray_dealloc,/* tp_dealloc */
    0,                            /* tp_print */
    0,                            /* tp_getattr */
    0,                            /* tp_setattr */
    0,                            /* tp_reserved */
    (reprfunc)PyMyArray_str,      /* tp_repr */
    0,                            /* tp_as_number */
    0,                            /* tp_as_sequence */
    0,                            /* tp_as_mapping */
    0,                            /* tp_hash  */
    0,                            /* tp_call */
    (reprfunc)PyMyArray_str,      /* tp_str */
    0,                            /* tp_getattro */
    0,                            /* tp_setattro */
    &PyMyArray_as_buffer,         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_NEWBUFFER, /* tp_flags */
    "PyMyArray object",           /* tp_doc */
    0,                            /* tp_traverse */
    0,                            /* tp_clear */
    0,                            /* tp_richcompare */
    0,                            /* tp_weaklistoffset */
    0,                            /* tp_iter */
    0,                            /* tp_iternext */
    0,                            /* tp_methods */
    0,                            /* tp_members */
    0,                            /* tp_getset */
    0,                            /* tp_base */
    0,                            /* tp_dict */
    0,                            /* tp_descr_get */
    0,                            /* tp_descr_set */
    0,                            /* tp_dictoffset */
    (initproc)PyMyArray_init,     /* tp_init */
};

static PyMethodDef buffer_functions[] = {
    {NULL,        NULL}    /* Sentinel */
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "buffer_test",
    "Module Doc",
    -1,
    buffer_functions;
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
PyInit_buffer_test(void)

#else

#define INITERROR return

/* Initialize this module. */
#ifdef __GNUC__
extern __attribute__((visibility("default")))
#else
#endif

PyMODINIT_FUNC
initbuffer_test(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *m= PyModule_Create(&moduledef);
#else
    PyObject *m= Py_InitModule("buffer_test", buffer_functions);
#endif
    if (m == NULL)
        INITERROR;
    PyMyArrayType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&PyMyArrayType) < 0)
        INITERROR;
    Py_INCREF(&PyMyArrayType);
    PyModule_AddObject(m, "PyMyArray", (PyObject *)&PyMyArrayType);
#if PY_MAJOR_VERSION >=3
    return m;
#endif
}
