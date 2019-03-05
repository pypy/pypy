#include "Python.h"

struct THPSize {
  PyTupleObject tuple;
} THPSize;

static PyObject * THPSize_pynew(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
  return PyTuple_Type.tp_new(type, args, kwargs);
}

static PyMappingMethods THPSize_as_mapping = {
    0, //PyTuple_Type.tp_as_mapping->mp_length,
    0,
    0
};


PyTypeObject THPSizeType = {
  PyVarObject_HEAD_INIT(0, 0)
  "torch.Size",                          /* tp_name */
  sizeof(THPSize),                       /* tp_basicsize */
  0,                                     /* tp_itemsize */
  0,                                     /* tp_dealloc */
  0,                                     /* tp_print */
  0,                                     /* tp_getattr */
  0,                                     /* tp_setattr */
  0,                                     /* tp_reserved */
  0,                /* tp_repr */
  0,                                     /* tp_as_number */
  0,                  /* tp_as_sequence */
  &THPSize_as_mapping,                   /* tp_as_mapping */
  0,                                     /* tp_hash  */
  0,                                     /* tp_call */
  0,                                     /* tp_str */
  0,                                     /* tp_getattro */
  0,                                     /* tp_setattro */
  0,                                     /* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,                    /* tp_flags */
  0,                               /* tp_doc */
  0,                                     /* tp_traverse */
  0,                                     /* tp_clear */
  0,                                     /* tp_richcompare */
  0,                                     /* tp_weaklistoffset */
  0,                                     /* tp_iter */
  0,                                     /* tp_iternext */
  0,                       /* tp_methods */
  0,                                     /* tp_members */
  0,                                     /* tp_getset */
  &PyTuple_Type,                         /* tp_base */
  0,                                     /* tp_dict */
  0,                                     /* tp_descr_get */
  0,                                     /* tp_descr_set */
  0,                                     /* tp_dictoffset */
  0,                                     /* tp_init */
  0,                                     /* tp_alloc */
  THPSize_pynew,                         /* tp_new */
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "THPSize",
    "Module Doc",
    -1,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
};

PyMODINIT_FUNC
PyInit_THPSize(void)
{
    PyObject *module = PyModule_Create(&moduledef);
    THPSize_as_mapping.mp_length = PyTuple_Type.tp_as_mapping->mp_length;
    if (PyType_Ready(&THPSizeType) < 0) {
        return NULL;
    }
    Py_INCREF(&THPSizeType);
    if (PyModule_AddObject(module, "Size", (PyObject*)&THPSizeType) < 0) {
        return NULL;
    }
    return module;
}
