#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_unicodeobject.h"

PyAPI_FUNC(PyObject *) PyUnicode_FromFormatV(const char *format, va_list vargs);
PyAPI_FUNC(PyObject *) PyUnicode_FromFormat(const char *format, ...);
PyAPI_FUNC(PyObject *) PyUnicode_FromUnicode(const wchar_t *u, Py_ssize_t size);
PyAPI_FUNC(PyObject *) PyUnicode_FromWideChar(const wchar_t *u, Py_ssize_t size);
PyAPI_FUNC(wchar_t*)   PyUnicode_AsUnicode(PyObject *unicode);
PyAPI_FUNC(Py_ssize_t) PyUnicode_GetSize(PyObject *unicode);
PyAPI_FUNC(Py_ssize_t) PyUnicode_AsWideChar(PyUnicodeObject *unicode,
                                             wchar_t *w, Py_ssize_t size);

#define Py_UNICODE_COPY(target, source, length)                         \
    Py_MEMCPY((target), (source), (length)*sizeof(wchar_t))
#define PyUnicode_Check(op) \
		 PyType_FastSubclass((op)->ob_type, Py_TPFLAGS_UNICODE_SUBCLASS)
#define PyUnicode_CheckExact(op) ((op)->ob_type == &PyUnicode_Type)

/* Fast access macros */
#define PyUnicode_GET_SIZE(op) \
    (((PyUnicodeObject *)(op))->length)
#define PyUnicode_GET_DATA_SIZE(op) \
    (((PyUnicodeObject *)(op))->length * sizeof(Py_UNICODE))
#define PyUnicode_AS_UNICODE(op) \
    (((PyUnicodeObject *)(op))->str)
#define PyUnicode_AS_DATA(op) \
    ((const char *)((PyUnicodeObject *)(op))->str)


#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
