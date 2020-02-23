#ifndef Py_SLICEOBJECT_H
#define Py_SLICEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

/* The unique ellipsis object "..." */

PyAPI_DATA(PyObject) _Py_EllipsisObject; /* Don't use this directly */

#define Py_Ellipsis (&_Py_EllipsisObject)

typedef struct {
    PyObject_HEAD
    PyObject *start;
    PyObject *stop;
    PyObject *step;
} PySliceObject;

#define PySlice_Check(op) (Py_TYPE(op) == &PySlice_Type)
    
#ifdef __cplusplus
}
#endif
#endif /* !Py_SLICEOBJECT_H */
