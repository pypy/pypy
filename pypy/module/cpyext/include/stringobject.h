
/* String object interface */

#ifndef Py_STRINGOBJECT_H
#define Py_STRINGOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

PyObject * PyString_FromStringAndSize(const char *, Py_ssize_t);

#ifdef __cplusplus
}
#endif
#endif
