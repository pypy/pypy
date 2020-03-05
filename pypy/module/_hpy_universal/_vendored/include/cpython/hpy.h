#ifndef HPy_CPYTHON_H
#define HPy_CPYTHON_H

/* XXX: it would be nice if we could include hpy.h WITHOUT bringing in all the
   stuff from Python.h, to make sure that people don't use the CPython API by
   mistake. How to achieve it, though? Is defining Py_LIMITED_API enough? */

/* XXX: should we:
 *    - enforce PY_SSIZE_T_CLEAN in hpy
 *    - make it optional
 *    - make it the default but give a way to disable it?
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#ifdef __GNUC__
#define HPyAPI_STORAGE __attribute__((unused)) static inline
#else
#define HPyAPI_STORAGE static inline
#endif /* __GNUC__ */

#define HPyAPI_FUNC(restype) HPyAPI_STORAGE restype

typedef struct { PyObject *_o; } HPy;
typedef Py_ssize_t HPy_ssize_t;

/* For internal usage only. These should be #undef at the end of this header.
   If you need to convert HPy to PyObject* and vice-versa, you should use the
   official way to do it (not implemented yet :)
*/
#define _h2py(x) (x._o)
#define _py2h(o) ((HPy){o})

#include "meth.h"

typedef struct _HPyContext_s {
    HPy h_None;
    HPy h_True;
    HPy h_False;
    HPy h_ValueError;
    HPy h_TypeError;
} *HPyContext;

/* XXX! should be defined only once, not once for every .c! */
static struct _HPyContext_s _global_ctx;

#define HPy_NULL ((HPy){NULL})
#define HPy_IsNull(x) ((x)._o == NULL)

// XXX: we need to decide whether these are part of the official API or not,
// and maybe introduce a better naming convetion. For now, they are needed for
// ujson
static inline HPy HPy_FromVoidP(void *p) { return (HPy){(PyObject*)p}; }
static inline void* HPy_AsVoidP(HPy h) { return (void*)h._o; }


HPyAPI_FUNC(HPyContext)
_HPyGetContext(void) {
    HPyContext ctx = &_global_ctx;
    if (HPy_IsNull(ctx->h_None)) {
        // XXX: we need to find a better way to check whether the ctx is
        // initialized or not
        ctx->h_None = _py2h(Py_None);
        ctx->h_True = _py2h(Py_True);
        ctx->h_False = _py2h(Py_False);
        ctx->h_ValueError = _py2h(PyExc_ValueError);
        ctx->h_TypeError = _py2h(PyExc_TypeError);
    }
    return ctx;
}


HPyAPI_FUNC(HPy)
HPy_Dup(HPyContext ctx, HPy handle)
{
    Py_XINCREF(_h2py(handle));
    return handle;
}

HPyAPI_FUNC(void)
HPy_Close(HPyContext ctx, HPy handle)
{
    Py_XDECREF(_h2py(handle));
}

/* moduleobject.h */
typedef PyModuleDef HPyModuleDef;

#define HPyModuleDef_HEAD_INIT PyModuleDef_HEAD_INIT

HPyAPI_FUNC(HPy)
HPyModule_Create(HPyContext ctx, HPyModuleDef *mdef) {
    return _py2h(PyModule_Create(mdef));
}

#define HPy_MODINIT(modname)                                   \
    static HPy init_##modname##_impl(HPyContext ctx);          \
    PyMODINIT_FUNC                                             \
    PyInit_##modname(void)                                     \
    {                                                          \
        return _h2py(init_##modname##_impl(_HPyGetContext())); \
    }

/* XXX: this function is copied&pasted THREE times:
 *     hpy_devel/include/hpy.h
 *     cpython-universal/api.c
 *     pypy/module/hpy_universal/src/getargs.c
 *
 * We need a way to share this kind of common code
 */

HPyAPI_FUNC(int)
HPyArg_Parse(HPyContext ctx, HPy *args, Py_ssize_t nargs, const char *fmt, ...)
{
    va_list vl;
    va_start(vl, fmt);
    const char *fmt1 = fmt;
    Py_ssize_t i = 0;

    while (*fmt1 != 0) {
        if (i >= nargs) {
            abort(); // XXX
        }
        switch (*fmt1++) {
        case 'l': {
            long *output = va_arg(vl, long *);
            long value = PyLong_AsLong(_h2py(args[i]));
            // XXX check for exceptions
            *output = value;
            break;
        }
        default:
            abort();  // XXX
        }
        i++;
    }
    if (i != nargs) {
        abort();   // XXX
    }

    va_end(vl);
    return 1;
}


HPyAPI_FUNC(HPy)
HPy_FromPyObject(HPyContext ctx, PyObject *obj)
{
    Py_XINCREF(obj);
    return _py2h(obj);
}

HPyAPI_FUNC(PyObject *)
HPy_AsPyObject(HPyContext ctx, HPy h)
{
    PyObject *result = _h2py(h);
    Py_XINCREF(result);
    return result;
}

/* expand impl functions as:
 *     static inline HPyLong_FromLong(...);
 *
 */
#define _HPy_IMPL_NAME(name) HPy##name
#include "../common/autogen_impl.h"
#undef _HPy_IMPL_NAME

#endif /* !HPy_CPYTHON_H */
