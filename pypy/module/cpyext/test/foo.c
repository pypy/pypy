#include "Python.h"
#include "structmember.h"

typedef struct {
    PyObject_HEAD
    int    foo;        /* the context holder */
    PyObject *foo_object;
    char *foo_string;
    char foo_string_inplace[5];
} fooobject;

static PyTypeObject footype;

static fooobject *
newfooobject(void)
{
    fooobject *foop;

    foop = PyObject_New(fooobject, &footype);
    if (foop == NULL)
        return NULL;

    foop->foo = 42;
    foop->foo_object = NULL;
    foop->foo_string = "Hello from PyPy";
    strncpy(foop->foo_string_inplace, "spam", 5);
    return foop;
}


/* foo methods */

static void
foo_dealloc(fooobject *foop)
{
    PyObject_Del(foop);
}


/* foo methods-as-attributes */

static PyObject *
foo_copy(fooobject *self)
{
    fooobject *foop;

    if ((foop = newfooobject()) == NULL)
        return NULL;

    foop->foo = self->foo;

    return (PyObject *)foop;
}

static PyObject *
foo_unset(fooobject *self)
{
    self->foo_string = NULL;
    Py_RETURN_NONE;
}


static PyMethodDef foo_methods[] = {
    {"copy",      (PyCFunction)foo_copy,      METH_NOARGS,  NULL},
    {"unset_string_member", (PyCFunction)foo_unset, METH_NOARGS, NULL},
    {NULL, NULL}                 /* sentinel */
};

static PyObject *
foo_get_name(PyObject *self, void *closure)
{
    return PyString_FromStringAndSize("Foo Example", 11);
}

static PyObject *
foo_get_foo(PyObject *self, void *closure)
{
  return PyInt_FromLong(((fooobject*)self)->foo);
}

static PyGetSetDef foo_getseters[] = {
    {"name",
     (getter)foo_get_name, NULL,
     NULL,
     NULL},
     {"foo",
     (getter)foo_get_foo, NULL,
     NULL,
     NULL},
    {NULL}  /* Sentinel */
};

static PyObject *
foo_repr(PyObject *self)
{
    PyObject *format;

    format = PyString_FromString("<Foo>");
    if (format == NULL) return NULL;
    return format;
}

static PyObject *
foo_call(PyObject *self, PyObject *args, PyObject *kwds)
{
    Py_INCREF(kwds);
    return kwds;
}

static PyMemberDef foo_members[] = {
    {"int_member", T_INT, offsetof(fooobject, foo), 0,
     "A helpful docstring."},
    {"int_member_readonly", T_INT, offsetof(fooobject, foo), READONLY,
     "A helpful docstring."},
    {"broken_member", 0xaffe, 0, 0, NULL},
    {"object_member", T_OBJECT, offsetof(fooobject, foo_object), 0,
     "A Python object."},
    {"object_member_ex", T_OBJECT_EX, offsetof(fooobject, foo_object), 0,
     "A Python object."},
    {"string_member", T_STRING, offsetof(fooobject, foo_string), 0,
     "A string."},
    {"string_member_inplace", T_STRING_INPLACE,
     offsetof(fooobject, foo_string_inplace), 0, "An inplace string."},
    {"char_member", T_CHAR, offsetof(fooobject, foo_string_inplace), 0, NULL},
    {NULL}  /* Sentinel */
};

static PyTypeObject footype = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "foo.foo",               /*tp_name*/
    sizeof(fooobject),       /*tp_size*/
    0,                       /*tp_itemsize*/
    /* methods */
    (destructor)foo_dealloc, /*tp_dealloc*/
    0,                       /*tp_print*/
    0,                       /*tp_getattr*/
    0,                       /*tp_setattr*/
    0,                       /*tp_compare*/
    foo_repr,                /*tp_repr*/
    0,                       /*tp_as_number*/
    0,                       /*tp_as_sequence*/
    0,                       /*tp_as_mapping*/
    0,                       /*tp_hash*/
    foo_call,                /*tp_call*/
    0,                       /*tp_str*/
    0,                       /*tp_getattro*/
    0,                       /*tp_setattro*/
    0,                       /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,      /*tp_flags*/
    0,                       /*tp_doc*/
    0,                       /*tp_traverse*/
    0,                       /*tp_clear*/
    0,                       /*tp_richcompare*/
    0,                       /*tp_weaklistoffset*/
    0,                       /*tp_iter*/
    0,                       /*tp_iternext*/
    foo_methods,             /*tp_methods*/
    foo_members,             /*tp_members*/
    foo_getseters,           /*tp_getset*/
};

typedef struct {
    PyUnicodeObject HEAD;
    int val;
} FuuObject;


void Fuu_init(FuuObject *self, PyObject *args, PyObject *kwargs) {
    self->val = 42;
}

static PyObject *
Fuu_escape(PyTypeObject* type, PyObject *args)
{
    Py_RETURN_TRUE;
}

static PyObject *
Fuu_get_val(FuuObject *self) {
    return PyInt_FromLong(self->val);
}

static PyMethodDef Fuu_methods[] = {
    {"escape", (PyCFunction) Fuu_escape, METH_VARARGS, NULL},
    {"get_val", (PyCFunction) Fuu_get_val, METH_NOARGS, NULL},
    {NULL}  /* Sentinel */
};

PyTypeObject FuuType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "foo.fuu",
    sizeof(FuuObject),
    0,
    0,          /*tp_dealloc*/
    0,          /*tp_print*/
    0,          /*tp_getattr*/
    0,          /*tp_setattr*/
    0,          /*tp_compare*/
    0,          /*tp_repr*/
    0,          /*tp_as_number*/
    0,          /*tp_as_sequence*/
    0,          /*tp_as_mapping*/
    0,          /*tp_hash */

    0,          /*tp_call*/
    0,          /*tp_str*/
    0,          /*tp_getattro*/
    0,          /*tp_setattro*/
    0,          /*tp_as_buffer*/

    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_CHECKTYPES, /*tp_flags*/
    0,          /*tp_doc*/

    0,          /*tp_traverse*/
    0,          /*tp_clear*/

    0,          /*tp_richcompare*/
    0,          /*tp_weaklistoffset*/

    0,          /*tp_iter*/
    0,          /*tp_iternext*/

    /* Attribute descriptor and subclassing stuff */

    Fuu_methods,/*tp_methods*/
    0,          /*tp_members*/
    0,          /*tp_getset*/
    0,          /*tp_base*/
    0,          /*tp_dict*/

    0,          /*tp_descr_get*/
    0,          /*tp_descr_set*/
    0,          /*tp_dictoffset*/

    Fuu_init,          /*tp_init*/
    0,          /*tp_alloc  will be set to PyType_GenericAlloc in module init*/
    0,          /*tp_new*/
    0,          /*tp_free  Low-level free-memory routine */
    0,          /*tp_is_gc For PyObject_IS_GC */
    0,          /*tp_bases*/
    0,          /*tp_mro method resolution order */
    0,          /*tp_cache*/
    0,          /*tp_subclasses*/
    0           /*tp_weaklist*/
};


/* foo functions */

static PyObject *
foo_new(PyObject *self, PyObject *args)
{
    fooobject *foop;

    if ((foop = newfooobject()) == NULL) {
        return NULL;
    }
    
    return (PyObject *)foop;
}

/* List of functions exported by this module */

static PyMethodDef foo_functions[] = {
    {"new",        (PyCFunction)foo_new, METH_NOARGS, NULL},
    {NULL,        NULL}    /* Sentinel */
};


/* Initialize this module. */

void initfoo(void)
{
    PyObject *m, *d;

    footype.tp_new = PyType_GenericNew;

    FuuType.tp_base = &PyUnicode_Type;

    if (PyType_Ready(&footype) < 0)
        return;
    if (PyType_Ready(&FuuType) < 0)
        return;
    m = Py_InitModule("foo", foo_functions);
    if (m == NULL)
        return;
    d = PyModule_GetDict(m);
    if (d) {
        if (PyDict_SetItemString(d, "fooType", (PyObject *)&footype) < 0)
            return;
        PyDict_SetItemString(d, "FuuType", (PyObject *) &FuuType);
    }
       /* No need to check the error here, the caller will do that */
}
