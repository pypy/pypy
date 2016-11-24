
/* dict object interface */

#ifndef Py_DICTOBJECT_H
#define Py_DICTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    PyObject *ob_keys; /* a private place to put keys during PyDict_Next */
} PyDictObject;

#ifdef __cplusplus
}
#endif
#endif /* !Py_DICTOBJECT_H */
