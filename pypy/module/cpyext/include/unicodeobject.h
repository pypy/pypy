#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif


typedef unsigned int Py_UCS4;
#ifdef HAVE_USABLE_WCHAR_T
#define PY_UNICODE_TYPE wchar_t
#elif Py_UNICODE_SIZE == 4
#define PY_UNICODE_TYPE Py_UCS4
#else
#define PY_UNICODE_TYPE unsigned short
#endif
typedef PY_UNICODE_TYPE Py_UNICODE;

#define Py_UNICODE_REPLACEMENT_CHARACTER ((Py_UNICODE) 0xFFFD)

typedef struct {
    PyObject_HEAD
    Py_UNICODE *buffer;
    Py_ssize_t size;
} PyUnicodeObject;


#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
