
/* Tuple object interface */

#ifndef Py_TUPLEOBJECT_H
#define Py_TUPLEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

/* defined in varargswrapper.c */
PyObject * PyTuple_Pack(Py_ssize_t, ...);

#define PyTuple_SET_ITEM PyTuple_SetItem
#define PyTuple_GET_ITEM PyTuple_GetItem


#ifdef __cplusplus
}
#endif
#endif /* !Py_TUPLEOBJECT_H */
