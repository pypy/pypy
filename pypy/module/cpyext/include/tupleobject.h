
/* Tuple object interface */

#ifndef Py_TUPLEOBJECT_H
#define Py_TUPLEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

PyObject * PyTuple_New(Py_ssize_t size);
PyObject * PyTuple_Pack(Py_ssize_t, ...);
int PyTuple_SetItem(PyObject *, Py_ssize_t, PyObject *);

#ifdef __cplusplus
}
#endif
#endif /* !Py_TUPLEOBJECT_H */
