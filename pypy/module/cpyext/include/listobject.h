#ifndef Py_LISTOBJECT_H
#define Py_LISTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyList_Check(op) \
		 PyType_FastSubclass((op)->ob_type, Py_TPFLAGS_LIST_SUBCLASS)
#define PyList_CheckExact(op) ((op)->ob_type == &PyList_Type)

PyAPI_FUNC(Py_ssize_t) _PyList_CheckExact(PyObject *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_LISTOBJECT_H */