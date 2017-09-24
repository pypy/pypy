
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
		 PyType_FastSubclass((op)->ob_type, Py_TPFLAGS_DICT_SUBCLASS)
#define PyDict_CheckExact(op) ((op)->ob_type == &PyDict_Type)

#ifdef __cplusplus
}
#endif
#endif /* !Py_DICTOBJECT_H */
