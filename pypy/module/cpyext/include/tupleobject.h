
/* Tuple object interface */

#ifndef Py_TUPLEOBJECT_H
#define Py_TUPLEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

/* defined in varargswrapper.c */
PyObject * PyTuple_Pack(Py_ssize_t, ...);

typedef struct {
    PyObject_HEAD
    PyObject **items;
    Py_ssize_t size;
} PyTupleObject;

#define PyTuple_GET_ITEM        PyTuple_GetItem

/* Macro, trading safety for speed */
#define PyTuple_GET_SIZE(op)    (((PyTupleObject *)(op))->size)

/* Macro, *only* to be used to fill in brand new tuples */
#define PyTuple_SET_ITEM(op, i, v) (((PyTupleObject *)(op))->items[i] = v)

#ifdef __cplusplus
}
#endif
#endif /* !Py_TUPLEOBJECT_H */
