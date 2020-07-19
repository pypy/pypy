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

#ifdef __GNUC__
#define _HPy_HIDDEN  __attribute__((visibility("hidden")))
#else
#define _HPy_HIDDEN
#endif /* __GNUC__ */

#define HPyAPI_RUNTIME_FUNC(restype) _HPy_HIDDEN restype

typedef struct { PyObject *_o; } HPy;
typedef Py_ssize_t HPy_ssize_t;

/* For internal usage only. These should be #undef at the end of this header.
   If you need to convert HPy to PyObject* and vice-versa, you should use the
   official way to do it (not implemented yet :)
*/
#define _h2py(x) (x._o)
#define _py2h(o) ((HPy){o})

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
#define _HPy_IMPL_NAME_NOPREFIX(name) HPy_##name
#include "../common/implementation.h"
#undef _HPy_IMPL_NAME_NOPREFIX
#undef _HPy_IMPL_NAME

#include "../common/cpy_types.h"

#include "../common/macros.h"
#include "../common/runtime/argparse.h"

#include "../common/hpyfunc.h"
#include "../common/hpydef.h"
#include "../common/hpytype.h"
#include "../common/hpymodule.h"
#include "../common/runtime/ctx_module.h"
#include "../common/runtime/ctx_type.h"


HPyAPI_FUNC(HPy)
HPyModule_Create(HPyContext ctx, HPyModuleDef *mdef)
{
    return ctx_Module_Create(ctx, mdef);
}

HPyAPI_FUNC(HPy)
HPyType_FromSpec(HPyContext ctx, HPyType_Spec *spec)
{
    return ctx_Type_FromSpec(ctx, spec);
}

HPyAPI_FUNC(HPy)
_HPy_New(HPyContext ctx, HPy h, void **data)
{
    return ctx_New(ctx, h, data);
}

HPyAPI_FUNC(void*)
_HPy_Cast(HPyContext ctx, HPy h)
{
    return ctx_Cast(ctx, h);
}

#endif /* !HPy_CPYTHON_H */
