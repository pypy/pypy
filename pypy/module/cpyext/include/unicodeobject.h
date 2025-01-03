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

/* Fast check to determine whether an object is ready. Equivalent to:
   PyUnicode_IS_COMPACT(op) || _PyUnicodeObject_CAST(op)->data.any */
static inline unsigned int PyUnicode_IS_READY(PyObject *op) {
    return _PyASCIIObject_CAST(op)->state.ready;
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_IS_READY(op) PyUnicode_IS_READY(_PyObject_CAST(op))
#endif

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
/* String contains only wstr byte characters.  This is only possible
   when the string was created with a legacy API and _PyUnicode_Ready()
   has not been called yet.  */
    PyUnicode_WCHAR_KIND = 0,
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

/* PyUnicode_READY() does less work than _PyUnicode_Ready() in the best
   case.  If the canonical representation is not yet set, it will still call
   _PyUnicode_Ready().
   Returns 0 on success and -1 on errors. */

/* In CPython this is a static inlined function. On PyPy, because we generate
 * and mangle the _PyUnicode_Ready function, and the generated declaration
 * appears in pypy_decls.h which is 'include'ed after this file, we cannot use
 * the static inline method and must make it a macro
 */
#define PyUnicode_READY(op)                        \
    (assert(PyUnicode_Check(op)),                       \
     (PyUnicode_IS_READY(op) ?                          \
      0 : _PyUnicode_Ready((PyObject *)(op))))

/* 
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_READY(op) PyUnicode_READY(_PyObject_CAST(op))
#endif
*/

/* --- Legacy deprecated API ---------------------------------------------- */

/* Return a read-only pointer to the Unicode object's internal
   Py_UNICODE buffer.
   If the wchar_t/Py_UNICODE representation is not yet available, this
   function will calculate it. */
Py_DEPRECATED(3.3) PyAPI_FUNC(Py_UNICODE *) PyUnicode_AsUnicode(
    PyObject *unicode           /* Unicode object */
    );


/* Fast access macros */

Py_DEPRECATED(3.3)
static inline Py_ssize_t PyUnicode_WSTR_LENGTH(PyObject *op)
{
    if (PyUnicode_IS_COMPACT_ASCII(op)) {
        return _PyASCIIObject_CAST(op)->length;
    }
    else {
        return _PyCompactUnicodeObject_CAST(op)->wstr_length;
    }
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_WSTR_LENGTH(op) PyUnicode_WSTR_LENGTH(_PyObject_CAST(op))
#endif

/* Returns the deprecated Py_UNICODE representation's size in code units
   (this includes surrogate pairs as 2 units).
   If the Py_UNICODE representation is not available, it will be computed
   on request.  Use PyUnicode_GET_LENGTH() for the length in code points. */

Py_DEPRECATED(3.3)
static inline Py_ssize_t PyUnicode_GET_SIZE(PyObject *op)
{
    _Py_COMP_DIAG_PUSH
    _Py_COMP_DIAG_IGNORE_DEPR_DECLS
    if (_PyASCIIObject_CAST(op)->wstr == _Py_NULL) {
        (void)PyUnicode_AsUnicode(op);
        assert(_PyASCIIObject_CAST(op)->wstr != _Py_NULL);
    }
    return PyUnicode_WSTR_LENGTH(op);
    _Py_COMP_DIAG_POP
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_GET_SIZE(op) PyUnicode_GET_SIZE(_PyObject_CAST(op))
#endif

Py_DEPRECATED(3.3)
static inline Py_ssize_t PyUnicode_GET_DATA_SIZE(PyObject *op)
{
    _Py_COMP_DIAG_PUSH
    _Py_COMP_DIAG_IGNORE_DEPR_DECLS
    return PyUnicode_GET_SIZE(op) * Py_UNICODE_SIZE;
    _Py_COMP_DIAG_POP
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_GET_DATA_SIZE(op) PyUnicode_GET_DATA_SIZE(_PyObject_CAST(op))
#endif

/* Alias for PyUnicode_AsUnicode().  This will create a wchar_t/Py_UNICODE
   representation on demand.  Using this macro is very inefficient now,
   try to port your code to use the new PyUnicode_*BYTE_DATA() macros or
   use PyUnicode_WRITE() and PyUnicode_READ(). */

Py_DEPRECATED(3.3)
static inline Py_UNICODE* PyUnicode_AS_UNICODE(PyObject *op)
{
    wchar_t *wstr = _PyASCIIObject_CAST(op)->wstr;
    if (wstr != _Py_NULL) {
        return wstr;
    }

    _Py_COMP_DIAG_PUSH
    _Py_COMP_DIAG_IGNORE_DEPR_DECLS
    return PyUnicode_AsUnicode(op);
    _Py_COMP_DIAG_POP
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_AS_UNICODE(op) PyUnicode_AS_UNICODE(_PyObject_CAST(op))
#endif

Py_DEPRECATED(3.3)
static inline const char* PyUnicode_AS_DATA(PyObject *op)
{
    _Py_COMP_DIAG_PUSH
    _Py_COMP_DIAG_IGNORE_DEPR_DECLS
    Py_UNICODE *data = PyUnicode_AS_UNICODE(op);
    // In C++, casting directly PyUnicode* to const char* is not valid
    return _Py_STATIC_CAST(const char*, _Py_STATIC_CAST(const void*, data));
    _Py_COMP_DIAG_POP
}
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 < 0x030b0000
#  define PyUnicode_AS_DATA(op) PyUnicode_AS_DATA(_PyObject_CAST(op))
#endif

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

/* Get the number of Py_UNICODE units in the
   string representation. */

Py_DEPRECATED(3.3) PyAPI_FUNC(Py_ssize_t) PyUnicode_GetSize(
    PyObject *unicode           /* Unicode object */
    );

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

#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
