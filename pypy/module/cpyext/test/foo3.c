#include <Python.h>
#include <stdio.h>

PyObject* foo3type_tp_new(PyTypeObject* metatype, PyObject* args, PyObject* kwds)
{
    printf("in foo3type_tp_new, preprocessing...\n");
    PyObject* newType = PyType_Type.tp_new(metatype, args, kwds);
    printf("in foo3type_tp_new, postprocessing...\n");
    return newType;
}

PyTypeObject Foo3Type_Type = {
    PyVarObject_HEAD_INIT(0, 0)
    /*tp_name*/             "Foo3.Type",
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
    /*tp_flags*/            Py_TPFLAGS_DEFAULT,
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
    /*tp_base*/             0,		//  set to &PyType_Type in module init function (why can it not be done here?)
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

#ifdef _WIN32
	__declspec(dllexport) void		// PyModINIT_FUNC is broken on PyPy/Windows
#else
	PyMODINIT_FUNC
#endif
initfoo3(void)
{
	PyObject* mod = Py_InitModule("Foo3", sbkMethods);
	Foo3Type_Type.tp_base = &PyType_Type;
	PyType_Ready(&Foo3Type_Type);
	PyModule_AddObject(mod, "Type", (PyObject*)&Foo3Type_Type);
}
