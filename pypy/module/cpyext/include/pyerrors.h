
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

PyAPI_FUNC(void) _Py_FatalErrorFunc(const char * func, const char *msg);

#define Py_FatalError(message) _Py_FatalErrorFunc(__func__, message)

#ifdef __cplusplus
}
#endif
#endif /* !Py_PYERRORS_H */
