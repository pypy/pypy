#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

/* start sync with cpython unicodeobject.h line 65 */
#ifndef SIZEOF_WCHAR_T
#error Must define SIZEOF_WCHAR_T
#endif

#define Py_UNICODE_SIZE SIZEOF_WCHAR_T

/* If wchar_t can be used for UCS-4 storage, set Py_UNICODE_WIDE.
   Otherwise, Unicode strings are stored as UCS-2 (with limited support
   for UTF-16) */

#if Py_UNICODE_SIZE >= 4
#define Py_UNICODE_WIDE
#endif

/* Set these flags if the platform has "wchar.h" and the
   wchar_t type is a 16-bit unsigned type */
/* #define HAVE_WCHAR_H */
/* #define HAVE_USABLE_WCHAR_T */

/* If the compiler provides a wchar_t type we try to support it
   through the interface functions PyUnicode_FromWideChar(),
   PyUnicode_AsWideChar() and PyUnicode_AsWideCharString(). */

#ifdef HAVE_USABLE_WCHAR_T
# ifndef HAVE_WCHAR_H
#  define HAVE_WCHAR_H
# endif
#endif

#ifdef HAVE_WCHAR_H
#  include <wchar.h>
#endif


#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_unicodeobject.h"

#define PyUnicode_Check(op) \
    PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_UNICODE_SUBCLASS)
#define PyUnicode_CheckExact(op) Py_IS_TYPE(op, &PyUnicode_Type)

/* --- Constants ---------------------------------------------------------- */

/* This Unicode character will be used as replacement character during
   decoding if the errors argument is set to "replace". Note: the
   Unicode character U+FFFD is the official REPLACEMENT CHARACTER in
   Unicode 3.0. */

#define Py_UNICODE_REPLACEMENT_CHARACTER ((Py_UCS4) 0xFFFD)

/* taken from cpython/Include/cpython/unicodeobject.h */

/* Py_UNICODE was the native Unicode storage format (code unit) used by
   Python and represents a single Unicode element in the Unicode type.
   With PEP 393, Py_UNICODE is deprecated and replaced with a
   typedef to wchar_t. */
#define PY_UNICODE_TYPE wchar_t
/* Py_DEPRECATED(3.3) */ typedef wchar_t Py_UNICODE;

/* --- Internal Unicode Operations ---------------------------------------- */

PyAPI_DATA(const unsigned char) _Py_ascii_whitespace[];

#ifndef USE_UNICODE_WCHAR_CACHE
#  define USE_UNICODE_WCHAR_CACHE 1
#endif /* USE_UNICODE_WCHAR_CACHE */

/* Since splitting on whitespace is an important use case, and
   whitespace in most situations is solely ASCII whitespace, we
   optimize for the common case by using a quick look-up table
   _Py_ascii_whitespace (see below) with an inlined check.

 */
#define Py_UNICODE_ISSPACE(ch) \
    ((Py_UCS4)(ch) < 128U ? _Py_ascii_whitespace[(ch)] : _PyUnicode_IsWhitespace(ch))

#define Py_UNICODE_ISLOWER(ch) _PyUnicode_IsLowercase(ch)
#define Py_UNICODE_ISUPPER(ch) _PyUnicode_IsUppercase(ch)
#define Py_UNICODE_ISTITLE(ch) _PyUnicode_IsTitlecase(ch)
#define Py_UNICODE_ISLINEBREAK(ch) _PyUnicode_IsLinebreak(ch)

#define Py_UNICODE_TOLOWER(ch) _PyUnicode_ToLowercase(ch)
#define Py_UNICODE_TOUPPER(ch) _PyUnicode_ToUppercase(ch)
#define Py_UNICODE_TOTITLE(ch) _PyUnicode_ToTitlecase(ch)

#define Py_UNICODE_ISDECIMAL(ch) _PyUnicode_IsDecimalDigit(ch)
#define Py_UNICODE_ISDIGIT(ch) _PyUnicode_IsDigit(ch)
#define Py_UNICODE_ISNUMERIC(ch) _PyUnicode_IsNumeric(ch)
#define Py_UNICODE_ISPRINTABLE(ch) _PyUnicode_IsPrintable(ch)

#define Py_UNICODE_TODECIMAL(ch) _PyUnicode_ToDecimalDigit(ch)
#define Py_UNICODE_TODIGIT(ch) _PyUnicode_ToDigit(ch)
#define Py_UNICODE_TONUMERIC(ch) _PyUnicode_ToNumeric(ch)

#define Py_UNICODE_ISALPHA(ch) _PyUnicode_IsAlpha(ch)

#define Py_UNICODE_ISALNUM(ch) \
   (Py_UNICODE_ISALPHA(ch) || \
    Py_UNICODE_ISDECIMAL(ch) || \
    Py_UNICODE_ISDIGIT(ch) || \
    Py_UNICODE_ISNUMERIC(ch))

/* macros to work with surrogates */
#define Py_UNICODE_IS_SURROGATE(ch) (0xD800 <= (ch) && (ch) <= 0xDFFF)
#define Py_UNICODE_IS_HIGH_SURROGATE(ch) (0xD800 <= (ch) && (ch) <= 0xDBFF)
#define Py_UNICODE_IS_LOW_SURROGATE(ch) (0xDC00 <= (ch) && (ch) <= 0xDFFF)
/* Join two surrogate characters and return a single Py_UCS4 value. */
#define Py_UNICODE_JOIN_SURROGATES(high, low)  \
    (((((Py_UCS4)(high) & 0x03FF) << 10) |      \
      ((Py_UCS4)(low) & 0x03FF)) + 0x10000)
/* high surrogate = top 10 bits added to D800 */
#define Py_UNICODE_HIGH_SURROGATE(ch) (0xD800 - (0x10000 >> 10) + ((ch) >> 10))
/* low surrogate = bottom 10 bits added to DC00 */
#define Py_UNICODE_LOW_SURROGATE(ch) (0xDC00 + ((ch) & 0x3FF))


#define _PyASCIIObject_CAST(op) \
    (assert(PyUnicode_Check(op)), \
     _Py_CAST(PyASCIIObject*, (op)))
#define _PyCompactUnicodeObject_CAST(op) \
    (assert(PyUnicode_Check(op)), \
     _Py_CAST(PyCompactUnicodeObject*, (op)))
#define _PyUnicodeObject_CAST(op) \
    (assert(PyUnicode_Check(op)), \
     _Py_CAST(PyUnicodeObject*, (op)))

/* --- Flexible String Representation Helper Macros (PEP 393) -------------- */

/* Values for PyASCIIObject.state: */

/* Interning state. */
#define SSTATE_NOT_INTERNED 0
#define SSTATE_INTERNED_MORTAL 1
#define SSTATE_INTERNED_IMMORTAL 2

/* Use only if you know it's a string */
static inline unsigned int PyUnicode_CHECK_INTERNED(PyObject *op) {
    return _PyASCIIObject_CAST(op)->state.interned;
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_CHECK_INTERNED(op) PyUnicode_CHECK_INTERNED(_PyObject_CAST(op))
#endif

/* For backward compatibility. PyPy's unicode objects are always in their
   canonical representation once they exist. */
static inline unsigned int PyUnicode_IS_READY(PyObject* Py_UNUSED(op)) {
    return 1;
}
#define PyUnicode_IS_READY(op) PyUnicode_IS_READY(_PyObject_CAST(op))

/* Return true if the string contains only ASCII characters, or 0 if not. The
   string may be compact (PyUnicode_IS_COMPACT_ASCII) or not, but must be
   ready. */
static inline unsigned int PyUnicode_IS_ASCII(PyObject *op) {
    assert(PyUnicode_IS_READY(op));
    return _PyASCIIObject_CAST(op)->state.ascii;
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_IS_ASCII(op) PyUnicode_IS_ASCII(_PyObject_CAST(op))
#endif

/* Return true if the string is compact or 0 if not.
   No type checks or Ready calls are performed. */
static inline unsigned int PyUnicode_IS_COMPACT(PyObject *op) {
    return _PyASCIIObject_CAST(op)->state.compact;
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_IS_COMPACT(op) PyUnicode_IS_COMPACT(_PyObject_CAST(op))
#endif

/* Return true if the string is a compact ASCII string (use PyASCIIObject
   structure), or 0 if not.  No type checks or Ready calls are performed. */
static inline int PyUnicode_IS_COMPACT_ASCII(PyObject *op) {
    return (_PyASCIIObject_CAST(op)->state.ascii && PyUnicode_IS_COMPACT(op));
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_IS_COMPACT_ASCII(op) PyUnicode_IS_COMPACT_ASCII(_PyObject_CAST(op))
#endif

enum PyUnicode_Kind {
/* Return values of the PyUnicode_KIND() function: */
    PyUnicode_1BYTE_KIND = 1,
    PyUnicode_2BYTE_KIND = 2,
    PyUnicode_4BYTE_KIND = 4
};

/* Return one of the PyUnicode_*_KIND values defined above. */
#define PyUnicode_KIND(op) \
    (assert(PyUnicode_IS_READY(op)), \
     _PyASCIIObject_CAST(op)->state.kind)

/* Return a void pointer to the raw unicode buffer. */
static inline void* _PyUnicode_COMPACT_DATA(PyObject *op) {
    if (PyUnicode_IS_ASCII(op)) {
        return _Py_STATIC_CAST(void*, (_PyASCIIObject_CAST(op) + 1));
    }
    return _Py_STATIC_CAST(void*, (_PyCompactUnicodeObject_CAST(op) + 1));
}

static inline void* _PyUnicode_NONCOMPACT_DATA(PyObject *op) {
    void *data;
    assert(!PyUnicode_IS_COMPACT(op));
    /* data = _PyUnicodeObject_CAST(op)->data.any; */
    data = _PyUnicodeObject_CAST(op)->data;
    assert(data != NULL);
    return data;
}

static inline void* PyUnicode_DATA(PyObject *op) {
    if (PyUnicode_IS_COMPACT(op)) {
        return _PyUnicode_COMPACT_DATA(op);
    }
    return _PyUnicode_NONCOMPACT_DATA(op);
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_DATA(op) PyUnicode_DATA(_PyObject_CAST(op))
#endif

/* Return pointers to the canonical representation cast to unsigned char,
   Py_UCS2, or Py_UCS4 for direct character access.
   No checks are performed, use PyUnicode_KIND() before to ensure
   these will work correctly. */

#define PyUnicode_1BYTE_DATA(op) _Py_STATIC_CAST(Py_UCS1*, PyUnicode_DATA(op))
#define PyUnicode_2BYTE_DATA(op) _Py_STATIC_CAST(Py_UCS2*, PyUnicode_DATA(op))
#define PyUnicode_4BYTE_DATA(op) _Py_STATIC_CAST(Py_UCS4*, PyUnicode_DATA(op))

/* Returns the length of the unicode string. The caller has to make sure that
   the string has it's canonical representation set before calling
   this function.  Call PyUnicode_(FAST_)Ready to ensure that. */
static inline Py_ssize_t PyUnicode_GET_LENGTH(PyObject *op) {
    assert(PyUnicode_IS_READY(op));
    return _PyASCIIObject_CAST(op)->length;
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_GET_LENGTH(op) PyUnicode_GET_LENGTH(_PyObject_CAST(op))
#endif

/* Write into the canonical representation, this function does not do any sanity
   checks and is intended for usage in loops.  The caller should cache the
   kind and data pointers obtained from other function calls.
   index is the index in the string (starts at 0) and value is the new
   code point value which should be written to that location. */
static inline void PyUnicode_WRITE(int kind, void *data,
                                   Py_ssize_t index, Py_UCS4 value)
{
    if (kind == PyUnicode_1BYTE_KIND) {
        assert(value <= 0xffU);
        _Py_STATIC_CAST(Py_UCS1*, data)[index] = _Py_STATIC_CAST(Py_UCS1, value);
    }
    else if (kind == PyUnicode_2BYTE_KIND) {
        assert(value <= 0xffffU);
        _Py_STATIC_CAST(Py_UCS2*, data)[index] = _Py_STATIC_CAST(Py_UCS2, value);
    }
    else {
        assert(kind == PyUnicode_4BYTE_KIND);
        assert(value <= 0x10ffffU);
        _Py_STATIC_CAST(Py_UCS4*, data)[index] = value;
    }
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#define PyUnicode_WRITE(kind, data, index, value) \
    PyUnicode_WRITE(_Py_STATIC_CAST(int, kind), _Py_CAST(void*, data), \
                    (index), _Py_STATIC_CAST(Py_UCS4, value))
#endif

/* Read a code point from the string's canonical representation.  No checks
   or ready calls are performed. */
static inline Py_UCS4 PyUnicode_READ(int kind,
                                     const void *data, Py_ssize_t index)
{
    if (kind == PyUnicode_1BYTE_KIND) {
        return _Py_STATIC_CAST(const Py_UCS1*, data)[index];
    }
    if (kind == PyUnicode_2BYTE_KIND) {
        return _Py_STATIC_CAST(const Py_UCS2*, data)[index];
    }
    assert(kind == PyUnicode_4BYTE_KIND);
    return _Py_STATIC_CAST(const Py_UCS4*, data)[index];
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#define PyUnicode_READ(kind, data, index) \
    PyUnicode_READ(_Py_STATIC_CAST(int, kind), \
                   _Py_STATIC_CAST(const void*, data), \
                   (index))
#endif

/* PyUnicode_READ_CHAR() is less efficient than PyUnicode_READ() because it
   calls PyUnicode_KIND() and might call it twice.  For single reads, use
   PyUnicode_READ_CHAR, for multiple consecutive reads callers should
   cache kind and use PyUnicode_READ instead. */
static inline Py_UCS4 PyUnicode_READ_CHAR(PyObject *unicode, Py_ssize_t index)
{
    int kind;
    assert(PyUnicode_IS_READY(unicode));
    kind = PyUnicode_KIND(unicode);
    if (kind == PyUnicode_1BYTE_KIND) {
        return PyUnicode_1BYTE_DATA(unicode)[index];
    }
    if (kind == PyUnicode_2BYTE_KIND) {
        return PyUnicode_2BYTE_DATA(unicode)[index];
    }
    assert(kind == PyUnicode_4BYTE_KIND);
    return PyUnicode_4BYTE_DATA(unicode)[index];
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_READ_CHAR(unicode, index) \
       PyUnicode_READ_CHAR(_PyObject_CAST(unicode), (index))
#endif

/* Return a maximum character value which is suitable for creating another
   string based on op.  This is always an approximation but more efficient
   than iterating over the string. */
static inline Py_UCS4 PyUnicode_MAX_CHAR_VALUE(PyObject *op)
{
    int kind;

    assert(PyUnicode_IS_READY(op));
    if (PyUnicode_IS_ASCII(op)) {
        return 0x7fU;
    }

    kind = PyUnicode_KIND(op);
    if (kind == PyUnicode_1BYTE_KIND) {
       return 0xffU;
    }
    if (kind == PyUnicode_2BYTE_KIND) {
        return 0xffffU;
    }
    assert(kind == PyUnicode_4BYTE_KIND);
    return 0x10ffffU;
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_MAX_CHAR_VALUE(op) \
       PyUnicode_MAX_CHAR_VALUE(_PyObject_CAST(op))
#endif

/* === Public API ========================================================= */

/* For backward compatibility. PyPy's unicode objects are always in their
   canonical representation once they exist, so this always succeeds. */
static inline int PyUnicode_READY(PyObject* Py_UNUSED(op))
{
    return 0;
}
#define PyUnicode_READY(op) PyUnicode_READY(_PyObject_CAST(op))

#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 >= 0x03030000
/* Get the length of the Unicode object. */

PyAPI_FUNC(Py_ssize_t) PyUnicode_GetLength(
    PyObject *unicode
);
#endif

/* Returns a pointer to the default encoding (UTF-8) of the
   Unicode object unicode.

   Like PyUnicode_AsUTF8AndSize(), this also caches the UTF-8 representation
   in the unicodeobject.

   _PyUnicode_AsString is a #define for PyUnicode_AsUTF8 to
   support the previous internal function with the same behaviour.

   Use of this API is DEPRECATED since no size information can be
   extracted from the returned data.

   *** This API is for interpreter INTERNAL USE ONLY and will likely
   *** be removed or changed for Python 3.1.

   *** If you need to access the Unicode object as UTF-8 bytes string,
   *** please use PyUnicode_AsUTF8String() instead.

*/
#ifndef Py_LIMITED_API
#define _PyUnicode_AsString PyUnicode_AsUTF8
#endif

PyAPI_FUNC(double) _PyUnicode_ToNumeric(
    Py_UCS4 ch       /* Unicode character */
    );

PyAPI_FUNC(int) _PyUnicode_IsWhitespace(
    const Py_UCS4 ch         /* Unicode character */
    );

PyAPI_FUNC(int) _PyUnicode_IsLinebreak(
    const Py_UCS4 ch         /* Unicode character */
    );

/* end of cpython/unicodeobject.h, back to ./unicodeobject.h */

PyAPI_FUNC(PyObject *) PyUnicode_FromFormatV(
    const char *format,   /* ASCII-encoded string  */
    va_list vargs
    );
PyAPI_FUNC(PyObject *) PyUnicode_FromFormat(
    const char *format,   /* ASCII-encoded string  */
    ...
    );

/* --- wchar_t support for platforms which support it --------------------- */

#ifdef HAVE_WCHAR_H

/* Create a Unicode Object from the wchar_t buffer w of the given
   size.

   The buffer is copied into the new object. */

PyAPI_FUNC(PyObject*) PyUnicode_FromWideChar(
    const wchar_t *w,           /* wchar_t buffer */
    Py_ssize_t size             /* size of buffer */
    );

/* Convert the Unicode object to a wide character string. The output string
   always ends with a nul character. If size is not NULL, write the number of
   wide characters (excluding the null character) into *size.

   Returns a buffer allocated by PyMem_Malloc() (use PyMem_Free() to free it)
   on success. On error, returns NULL, *size is undefined and raises a
   MemoryError. */

PyAPI_FUNC(wchar_t*) PyUnicode_AsWideCharString(
    PyObject *unicode,          /* Unicode object */
    Py_ssize_t *size            /* number of characters of the result */
    );

#endif

/* Returns a pointer to the default encoding (UTF-8) of the
   Unicode object unicode and the size of the encoded representation
   in bytes stored in *size.

   In case of an error, no *size is set.

   This function caches the UTF-8 encoded string in the unicodeobject
   and subsequent calls will return the same string.  The memory is released
   when the unicodeobject is deallocated.

*/

#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 >= 0x030A0000
PyAPI_FUNC(char *) PyUnicode_AsUTF8AndSize(
    PyObject *unicode,
    Py_ssize_t *size);
#endif

/* Concat two strings, put the result in *pleft and drop the right object
   (sets *pleft to NULL on error) */

PyAPI_FUNC(void) PyUnicode_AppendAndDel(
    PyObject **pleft,           /* Pointer to left string */
    PyObject *right             /* Right string */
    );


/* abi3/limited-API shims */
PyAPI_FUNC(PyObject*) PyUnicode_Partition(PyObject *s,  PyObject *sep);
PyAPI_FUNC(PyObject*) PyUnicode_RPartition(PyObject *s,  PyObject *sep);
PyAPI_FUNC(PyObject*) PyUnicode_RSplit(PyObject *s,  PyObject *sep,  Py_ssize_t maxsplit);
PyAPI_FUNC(PyObject *) PyUnicode_Translate(PyObject *str,  PyObject *table,  const char *errors);
PyAPI_FUNC(PyObject *) PyUnicode_RichCompare(PyObject *left,  PyObject *right,  int op);
PyAPI_FUNC(int) PyUnicode_IsIdentifier(PyObject *s);
PyAPI_FUNC(PyObject*) PyUnicode_AsCharmapString(PyObject *unicode,  PyObject *mapping);
PyAPI_FUNC(PyObject*) PyUnicode_DecodeCharmap(const char *string,  Py_ssize_t length,  PyObject *mapping,  const char *errors);
PyAPI_FUNC(PyObject*) PyUnicode_BuildEncodingMap(PyObject* string);
PyAPI_FUNC(PyObject*) PyUnicode_AsDecodedObject(PyObject *unicode,  const char *encoding,  const char *errors);
PyAPI_FUNC(PyObject*) PyUnicode_AsDecodedUnicode(PyObject *unicode,  const char *encoding,  const char *errors);
PyAPI_FUNC(PyObject*) PyUnicode_AsEncodedUnicode(PyObject *unicode,  const char *encoding,  const char *errors);
PyAPI_FUNC(PyObject*) PyUnicode_DecodeUnicodeEscape(const char *string,  Py_ssize_t length,  const char *errors);
PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF7(const char *string,  Py_ssize_t length,  const char *errors);
PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF7Stateful(const char *string,  Py_ssize_t length,  const char *errors,  Py_ssize_t *consumed);
PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF8Stateful(const char *string,  Py_ssize_t length,  const char *errors,  Py_ssize_t *consumed);
PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF16Stateful(const char *string,  Py_ssize_t length,  const char *errors,  int *byteorder,  Py_ssize_t *consumed);
PyAPI_FUNC(PyObject*) PyUnicode_DecodeUTF32Stateful(const char *string,  Py_ssize_t length,  const char *errors,  int *byteorder,  Py_ssize_t *consumed);

#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
