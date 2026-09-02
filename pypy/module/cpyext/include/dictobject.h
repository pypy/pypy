
/* dict object interface */

#ifndef Py_DICTOBJECT_H
#define Py_DICTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    PyObject *_tmpkeys; /* a private place to put keys during PyDict_Next */
} PyDictObject;

#define PyDict_Check(op) \
		 PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_DICT_SUBCLASS)
#define PyDict_CheckExact(op) (Py_TYPE(op) == &PyDict_Type)
#define PyDict_GET_SIZE(op)  PyObject_Length(op)


/* abi3/limited-API shims */
#define PyDictKeys_Check(op) PyObject_TypeCheck((op), &PyDictKeys_Type)
#define PyDictValues_Check(op) PyObject_TypeCheck((op), &PyDictValues_Type)
#define PyDictItems_Check(op) PyObject_TypeCheck((op), &PyDictItems_Type)
#define PyDictViewSet_Check(op) (PyDictKeys_Check(op) || PyDictItems_Check(op))
PyAPI_FUNC(int) PyDict_MergeFromSeq2(PyObject *d, PyObject *seq2, int override);

#ifdef __cplusplus
}
#endif
#endif /* !Py_DICTOBJECT_H */
