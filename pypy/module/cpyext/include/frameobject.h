#ifndef Py_FRAMEOBJECT_H
#define Py_FRAMEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct _frame {
    PyObject_HEAD
    struct _frame *f_back;      /* previous frame, or NULL */
    PyCodeObject *f_code;
    PyObject *f_globals;
    PyObject *f_locals;
    int f_lineno;
} PyFrameObject;

/* PyPy does not split the frame object into a boxed PyFrameObject and an
   unboxed _PyInterpreterFrame the way CPython 3.11+ does: PyFrameObject
   already plays both roles, so the two types are simply aliased here. */
typedef PyFrameObject _PyInterpreterFrame;

#define PyFrame_Check(op) Py_IS_TYPE((op), &PyFrame_Type)

#ifdef __cplusplus
}
#endif
#endif /* !Py_FRAMEOBJECT_H */
