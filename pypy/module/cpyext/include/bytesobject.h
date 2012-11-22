
/* String object interface */

#ifndef Py_BYTESOBJECT_H
#define Py_BYTESOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyBytes_GET_SIZE(op) PyBytes_Size(op)
#define PyBytes_AS_STRING(op) PyBytes_AsString(op)

typedef struct {
    PyObject_HEAD
    char* buffer;
    Py_ssize_t size;
} PyBytesObject;

#define PyByteArray_Check(obj) \
    PyObject_IsInstance(obj, (PyObject *)&PyByteArray_Type)

#ifdef __cplusplus
}
#endif
#endif
