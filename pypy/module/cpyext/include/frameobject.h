#ifndef Py_FRAMEOBJECT_H
#define Py_FRAMEOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    PyCodeObject *f_code;
    PyObject *f_globals;
    int f_lineno;
} PyFrameObject;

#ifdef __cplusplus
}
#endif
#endif /* !Py_FRAMEOBJECT_H */
