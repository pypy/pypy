#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif

#include <cpyext_unicodeobject.h>

PyAPI_FUNC(PyObject *) PyUnicode_FromFormatV(const char *format, va_list vargs);
PyAPI_FUNC(PyObject *) PyUnicode_FromFormat(const char *format, ...);

PyAPI_FUNC(wchar_t*) PyUnicode_AsWideCharString(PyObject *unicode, Py_ssize_t *size);

Py_LOCAL_INLINE(size_t) Py_UNICODE_strlen(const Py_UNICODE *u)
{
    int res = 0;
    while(*u++)
        res++;
    return res;
}

Py_LOCAL_INLINE(int)
Py_UNICODE_strcmp(const Py_UNICODE *s1, const Py_UNICODE *s2)
{
    while (*s1 && *s2 && *s1 == *s2)
        s1++, s2++;
    if (*s1 && *s2)
        return (*s1 < *s2) ? -1 : +1;
    if (*s1)
        return 1;
    if (*s2)
        return -1;
    return 0;
}

#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
