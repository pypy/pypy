
/* Tuple object interface */

#ifndef Py_TUPLEOBJECT_H
#define Py_TUPLEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    Py_ssize_t ob_size;
    PyObject **ob_item;    /* XXX optimize to ob_item[] */
} PyTupleObject;

/* defined in varargswrapper.c */
PyAPI_FUNC(PyObject *) PyTuple_Pack(Py_ssize_t, ...);

/* Macro, trading safety for speed */
#define PyTuple_GET_ITEM(op, i) (((PyTupleObject *)(op))->ob_item[i])
#define PyTuple_GET_SIZE(op)    Py_SIZE(op)

/* Macro, *only* to be used to fill in brand new tuples */
#define PyTuple_SET_ITEM(op, i, v) (((PyTupleObject *)(op))->ob_item[i] = v)


#ifdef __cplusplus
}
#endif
#endif /* !Py_TUPLEOBJECT_H */
