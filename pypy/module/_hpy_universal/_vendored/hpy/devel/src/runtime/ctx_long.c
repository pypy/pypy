#include <Python.h>
#include "hpy.h"

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif

// just for better readability
#define SIZEOF_INT32 4
#define SIZEOF_INT64 8

HPyAPI_IMPL HPy ctx_Long_FromInt32_t(HPyContext *ctx, int32_t value) {
#if SIZEOF_LONG >= SIZEOF_INT32
     return _py2h(PyLong_FromLong((long)value));
#else
#error "unsupported SIZEOF_LONG"
#endif
}

HPyAPI_IMPL HPy ctx_Long_FromUInt32_t(HPyContext *ctx, uint32_t value) {
#if SIZEOF_LONG >= SIZEOF_INT32
     return _py2h(PyLong_FromUnsignedLong((unsigned long)value));
#else
#error "unsupported SIZEOF_LONG"
#endif
}

HPyAPI_IMPL HPy ctx_Long_FromInt64_t(HPyContext *ctx, int64_t v) {
#if SIZEOF_LONG >= SIZEOF_INT64
     return _py2h(PyLong_FromLong((long)v));
#elif SIZEOF_LONG_LONG >= SIZEOF_INT64
     return _py2h(PyLong_FromLongLong((long long)v));
#else
#error "unsupported SIZEOF_LONG_LONG"
#endif
}

HPyAPI_IMPL HPy ctx_Long_FromUInt64_t(HPyContext *ctx, uint64_t v) {
#if SIZEOF_LONG >= SIZEOF_INT64
     return _py2h(PyLong_FromUnsignedLong((unsigned long)v));
#elif SIZEOF_LONG_LONG >= SIZEOF_INT64
     return _py2h(PyLong_FromUnsignedLongLong((unsigned long long)v));
#else
#error "unsupported SIZEOF_LONG_LONG"
#endif
}

HPyAPI_IMPL int32_t ctx_Long_AsInt32_t(HPyContext *ctx, HPy h) {
     long lres = PyLong_AsLong(_h2py(h));
#if SIZEOF_LONG == SIZEOF_INT32
     return (int32_t) lres;
#elif SIZEOF_LONG >= SIZEOF_INT32
     int32_t i32res = (int32_t) lres;
     if (lres == (long) i32res)
         return i32res;
    PyErr_SetString(PyExc_OverflowError,
                    "Python int too large to convert to C int32_t");
    return (int32_t) -1;
#else
#error "unsupported SIZEOF_LONG"
#endif
}

HPyAPI_IMPL uint32_t ctx_Long_AsUInt32_t(HPyContext *ctx, HPy h) {
     unsigned long lres = PyLong_AsUnsignedLong(_h2py(h));
#if SIZEOF_LONG == SIZEOF_INT32
     return (uint32_t) lres;
#elif SIZEOF_LONG >= SIZEOF_INT32
     uint32_t ui32res = (uint32_t) lres;
     if (lres == (unsigned long) ui32res)
         return ui32res;
    PyErr_SetString(PyExc_OverflowError,
                    "Python int too large to convert to C uint32_t");
    return (uint32_t) -1;
#else
#error "unsupported SIZEOF_LONG"
#endif
}

HPyAPI_IMPL uint32_t ctx_Long_AsUInt32_tMask(HPyContext *ctx, HPy h) {
     return (uint32_t) PyLong_AsUnsignedLongMask(_h2py(h));
}

HPyAPI_IMPL int64_t ctx_Long_AsInt64_t(HPyContext *ctx, HPy h) {
     long long lres = PyLong_AsLongLong(_h2py(h));
#if SIZEOF_LONG_LONG == SIZEOF_INT64
     return (int64_t) lres;
#elif SIZEOF_LONG_LONG >= SIZEOF_INT64
     int64_t i64res = (int64_t) lres;
     if (lres == (long long) i64res)
         return i64res;
    PyErr_SetString(PyExc_OverflowError,
                    "Python int too large to convert to C int64_t");
    return (int64_t) -1;
#else
#error "unsupported SIZEOF_LONG_LONG"
#endif
}

HPyAPI_IMPL uint64_t ctx_Long_AsUInt64_t(HPyContext *ctx, HPy h) {
     unsigned long long lres = PyLong_AsUnsignedLongLong(_h2py(h));
#if SIZEOF_LONG_LONG == SIZEOF_INT64
     return (uint64_t) lres;
#elif SIZEOF_LONG_LONG >= SIZEOF_INT64
     uint64_t ui64res = (uint64_t) lres;
     if (lres == (unsigned long long) ui64res)
         return ui64res;
    PyErr_SetString(PyExc_OverflowError,
                    "Python int too large to convert to C uint64_t");
    return (uint64_t) -1;
#else
#error "unsupported SIZEOF_LONG_LONG"
#endif
}

HPyAPI_IMPL uint64_t ctx_Long_AsUInt64_tMask(HPyContext *ctx, HPy h) {
     return (uint64_t) PyLong_AsUnsignedLongLongMask(_h2py(h));
}
