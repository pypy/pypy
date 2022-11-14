#ifndef Py_LISTOBJECT_H
#define Py_LISTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyList_Check(op) \
		 PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_LIST_SUBCLASS)
#define PyList_CheckExact(op) (Py_TYPE(op) == &PyList_Type)

PyAPI_FUNC(Py_ssize_t) _PyList_CheckExact(PyObject *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_LISTOBJECT_H */