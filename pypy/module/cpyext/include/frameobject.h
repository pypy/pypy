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

#ifndef Py_LIMITED_API
#define PyFrame_Check(op) Py_IS_TYPE((op), &PyFrame_Type)
#endif /* !Py_LIMITED_API */

#ifdef __cplusplus
}
#endif
#endif /* !Py_FRAMEOBJECT_H */
