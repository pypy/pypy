#ifndef Py_CODE_H
#define Py_CODE_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    PyObject *co_name;
    int co_argcount;
    int co_flags;
} PyCodeObject;

/* Masks for co_flags above */
/* These values are also in funcobject.py */
#define CO_OPTIMIZED	0x0001
#define CO_NEWLOCALS	0x0002
#define CO_VARARGS	0x0004
#define CO_VARKEYWORDS	0x0008
#define CO_NESTED       0x0010
#define CO_GENERATOR    0x0020

#ifdef __cplusplus
}
#endif
#endif /* !Py_CODE_H */
