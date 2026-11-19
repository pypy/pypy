/* A copy of pypy2's PyStringObject */

#ifndef Py_BYTESOBJECT_H
#define Py_BYTESOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include <stdarg.h>

#ifndef Py_LIMITED_API
#define PyBytes_GET_SIZE(op) PyBytes_Size(op)
#endif /* !Py_LIMITED_API */

/*
Type PyStringObject represents a character string.  An extra zero byte is
reserved at the end to ensure it is zero-terminated, but a size is
present so strings with null bytes in them can be represented.  This
is an immutable object type.

There are functions to create new string objects, to test
an object for string-ness, and to get the
string value.  The latter function returns a null pointer
if the object is not of the proper type.
There is a variant that takes an explicit size as well as a
variant that assumes a zero-terminated string.  Note that none of the
functions should be applied to nil objects.
*/

/* Caching the hash (ob_shash) saves recalculation of a string's hash value.
   Since it is part of the "public" interface PyPy must reimplement it. */

typedef struct {
    PyObject_VAR_HEAD
    Py_hash_t ob_shash;
    char ob_sval[1];

    /* Invariants:
     *     ob_sval contains space for 'ob_size+1' elements.
     *     ob_sval[ob_size] == 0.
     *     ob_shash is the hash of the string or -1 if not computed yet.
     */
} PyBytesObject;

#define PyBytes_Check(op) \
                 PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_BYTES_SUBCLASS)
#define PyBytes_CheckExact(op) (Py_TYPE(op) == &PyBytes_Type)

PyAPI_FUNC(PyObject *) PyBytes_FromFormatV(const char*, va_list);
PyAPI_FUNC(PyObject *) PyBytes_FromFormat(const char*, ...);


/* abi3/limited-API shims */
PyAPI_FUNC(PyObject *) PyBytes_Repr(PyObject *, int);
PyAPI_FUNC(PyObject *) PyBytes_DecodeEscape(const char *, Py_ssize_t, const char *, Py_ssize_t, const char *);

#ifdef __cplusplus
}
#endif
#endif
