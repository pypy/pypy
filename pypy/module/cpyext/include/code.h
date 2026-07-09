#ifndef Py_CODE_H
#define Py_CODE_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    PyObject *co_name;
    PyObject *co_filename;
    int co_argcount;
    int co_flags;
} PyCodeObject;

/* Masks for co_flags above */
/* These values are also in funcobject.py */
#define CO_OPTIMIZED    0x0001
#define CO_NEWLOCALS    0x0002
#define CO_VARARGS      0x0004
#define CO_VARKEYWORDS  0x0008
#define CO_NESTED       0x0010
#define CO_GENERATOR    0x0020
  
/* The CO_COROUTINE flag is set for coroutine functions (defined with
   ``async def`` keywords) */
#define CO_COROUTINE            0x0080
#define CO_ITERABLE_COROUTINE   0x0100

#define CO_FUTURE_DIVISION         0x020000
#define CO_FUTURE_ABSOLUTE_IMPORT  0x040000
#define CO_FUTURE_WITH_STATEMENT   0x080000
#define CO_FUTURE_PRINT_FUNCTION   0x100000
#define CO_FUTURE_UNICODE_LITERALS 0x200000

// Old names -- remove when this API changes.
// Macros (not static inline wrappers) so the target functions need not be
// declared when this header is compiled on its own, e.g. during the cpyext
// platform check before api.py has generated pypy_decl.h.
#define PyCode_New PyUnstable_Code_New
#define PyCode_NewWithPosOnlyArgs PyUnstable_Code_NewWithPosOnlyArgs


#ifdef __cplusplus
}
#endif
#endif /* !Py_CODE_H */
