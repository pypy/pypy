
/* Exception interface */

#ifndef Py_PYERRORS_H
#define Py_PYERRORS_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyExceptionClass_Check(x)                                       \
    ((PyType_Check((x)) &&                                              \
      PyType_FastSubclass((PyTypeObject*)(x), Py_TPFLAGS_BASE_EXC_SUBCLASS)))

#define PyExceptionInstance_Check(x)                                    \
    (PyObject_IsSubclass((PyObject *)Py_TYPE(x), PyExc_BaseException))

#define PyExc_EnvironmentError PyExc_OSError
#define PyExc_IOError PyExc_OSError

#ifdef MS_WINDOWS
#define PyExc_WindowsError PyExc_OSError
#endif

PyAPI_FUNC(PyObject *) PyErr_NewException(const char *name, PyObject *base, PyObject *dict);
PyAPI_FUNC(PyObject *) PyErr_NewExceptionWithDoc(const char *name, const char *doc, PyObject *base, PyObject *dict);
PyAPI_FUNC(PyObject *) PyErr_Format(PyObject *exception, const char *format, ...);
PyAPI_FUNC(PyObject *) _PyErr_FormatFromCause(PyObject *exception, const char *format, ...);
PyAPI_FUNC(PyObject *) PyErr_FormatV(PyObject *exception, const char *format, va_list vargs);

#include <stdarg.h>
PyAPI_FUNC(int) PyOS_snprintf(char *str, size_t size, const  char  *format, ...);
PyAPI_FUNC(int) PyOS_vsnprintf(char *str, size_t size, const char  *format, va_list va);

typedef struct {
    PyObject_HEAD       /* xxx PyException_HEAD in CPython */
    PyObject *value;
} PyStopIterationObject;

PyAPI_FUNC(void) _Py_NO_RETURN _Py_FatalErrorFunc(const char * func, const char *msg);

#define Py_FatalError(message) _Py_FatalErrorFunc(__func__, message)


/* abi3/limited-API shims */
PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_Create(const char *encoding,  const char *object, Py_ssize_t length, Py_ssize_t start, Py_ssize_t end, const char *reason);
PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_GetEncoding(PyObject *);
PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_GetObject(PyObject *);
PyAPI_FUNC(int) PyUnicodeDecodeError_GetStart(PyObject *, Py_ssize_t *);
PyAPI_FUNC(int) PyUnicodeDecodeError_GetEnd(PyObject *, Py_ssize_t *);
PyAPI_FUNC(PyObject *) PyUnicodeDecodeError_GetReason(PyObject *);
PyAPI_FUNC(int) PyUnicodeDecodeError_SetStart(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyUnicodeDecodeError_SetEnd(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyUnicodeDecodeError_SetReason(PyObject *exc, const char *reason);
PyAPI_FUNC(PyObject *) PyUnicodeEncodeError_GetEncoding(PyObject *);
PyAPI_FUNC(PyObject *) PyUnicodeEncodeError_GetObject(PyObject *);
PyAPI_FUNC(int) PyUnicodeEncodeError_GetStart(PyObject *, Py_ssize_t *);
PyAPI_FUNC(int) PyUnicodeEncodeError_GetEnd(PyObject *, Py_ssize_t *);
PyAPI_FUNC(PyObject *) PyUnicodeEncodeError_GetReason(PyObject *);
PyAPI_FUNC(int) PyUnicodeEncodeError_SetStart(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyUnicodeEncodeError_SetEnd(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyUnicodeEncodeError_SetReason(PyObject *exc, const char *reason);
PyAPI_FUNC(PyObject *) PyUnicodeTranslateError_GetObject(PyObject *);
PyAPI_FUNC(int) PyUnicodeTranslateError_GetStart(PyObject *, Py_ssize_t *);
PyAPI_FUNC(int) PyUnicodeTranslateError_GetEnd(PyObject *, Py_ssize_t *);
PyAPI_FUNC(PyObject *) PyUnicodeTranslateError_GetReason(PyObject *);
PyAPI_FUNC(int) PyUnicodeTranslateError_SetStart(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyUnicodeTranslateError_SetEnd(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyUnicodeTranslateError_SetReason(PyObject *exc, const char *reason);
PyAPI_FUNC(const char *) PyExceptionClass_Name(PyObject *);
PyAPI_FUNC(PyObject *) PyErr_ProgramText(const char *filename,  int lineno);
PyAPI_FUNC(PyObject *) PyErr_SetImportError(PyObject *, PyObject *, PyObject *);
PyAPI_FUNC(PyObject *) PyErr_SetImportErrorSubclass(PyObject *, PyObject *, PyObject *, PyObject *);
PyAPI_FUNC(void) PyErr_SyntaxLocation(const char *filename,  int lineno);
PyAPI_FUNC(void) PyErr_SyntaxLocationEx(const char *filename,  int lineno, int col_offset);

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYERRORS_H */
