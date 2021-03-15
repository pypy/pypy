#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_unicodeobject.h"

/* include for compatiblitly with CPython */
#ifdef HAVE_WCHAR_H
#  include <wchar.h>
#endif


PyAPI_FUNC(PyObject *) PyUnicode_FromFormatV(const char *format, va_list vargs);
PyAPI_FUNC(PyObject *) PyUnicode_FromFormat(const char *format, ...);

#define PyUnicode_Check(op) \
    PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_UNICODE_SUBCLASS)
#define PyUnicode_CheckExact(op) (Py_TYPE(op) == &PyUnicode_Type)

#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
