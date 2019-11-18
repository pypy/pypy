#ifndef HPy_UNIVERSAL_H
#define HPy_UNIVERSAL_H

#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>

typedef intptr_t HPy_ssize_t;
typedef struct { HPy_ssize_t _i; } HPy;

typedef struct _HPyContext_s *HPyContext;
struct _object;  /* that's PyObject inside CPython */
typedef struct _object *(*_HPy_CPyCFunction)(struct _object *self,
                                             struct _object *args);

#define HPy_NULL ((HPy){0})
#define HPy_IsNull(x) ((x)._i == 0)

typedef void (*_HPyMethodPairFunc)(void **out_func,
                                   _HPy_CPyCFunction *out_trampoline);

typedef struct {
    const char   *ml_name;   /* The name of the built-in function/method */
    _HPyMethodPairFunc ml_meth;   /* see HPy_FUNCTION() */
    int          ml_flags;   /* Combination of METH_xxx flags, which mostly
                                describe the args expected by the C func */
    const char   *ml_doc;    /* The __doc__ attribute, or NULL */
} HPyMethodDef;


#define HPyModuleDef_HEAD_INIT NULL

typedef struct {
    void *dummy; // this is needed because we put a comma after HPyModuleDef_HEAD_INIT :(
    const char* m_name;
    const char* m_doc;
    HPy_ssize_t m_size;
    HPyMethodDef *m_methods;
} HPyModuleDef;

#define _HPy_HIDDEN   __attribute__((visibility("hidden")))
#define HPy_MODINIT(modname)                                   \
    _HPy_HIDDEN HPyContext _ctx_for_trampolines;               \
    static HPy init_##modname##_impl(HPyContext ctx);          \
    HPy HPyInit_##modname(HPyContext ctx)                      \
    {                                                          \
        _ctx_for_trampolines = ctx;                            \
        return init_##modname##_impl(ctx);                     \
    }

#include "autogen_ctx.h"
#include "autogen_func.h"

extern HPyContext _ctx_for_trampolines;


#define HPy_METH_NOARGS(fnname)                                                \
    static HPy fnname##_impl(HPyContext ctx, HPy self);                        \
    static struct _object *                                                    \
    fnname##_trampoline(struct _object *self, struct _object *noargs)          \
    {                                                                          \
        return _HPy_CallRealFunctionFromTrampoline(                            \
            _ctx_for_trampolines, self, NULL, fnname##_impl, METH_NOARGS);     \
    }                                                                          \
    static void                                                                \
    fnname(void **out_func, _HPy_CPyCFunction *out_trampoline)                 \
    {                                                                          \
        *out_func = fnname##_impl;                                             \
        *out_trampoline = fnname##_trampoline;                                 \
    }

#define HPy_METH_O(fnname)                                                     \
    static HPy fnname##_impl(HPyContext ctx, HPy self, HPy arg);               \
    static struct _object *                                                    \
    fnname##_trampoline(struct _object *self, struct _object *arg)             \
    {                                                                          \
        return _HPy_CallRealFunctionFromTrampoline(                            \
            _ctx_for_trampolines, self, arg, fnname##_impl, METH_O);           \
    }                                                                          \
    static void                                                                \
    fnname(void **out_func, _HPy_CPyCFunction *out_trampoline)                 \
    {                                                                          \
        *out_func = fnname##_impl;                                             \
        *out_trampoline = fnname##_trampoline;                                 \
    }

#define HPy_METH_VARARGS(fnname)                                               \
    static HPy fnname##_impl(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t);\
    static struct _object *                                                    \
    fnname##_trampoline(struct _object *self, struct _object *args)            \
    {                                                                          \
        return _HPy_CallRealFunctionFromTrampoline(                            \
            _ctx_for_trampolines, self, args, fnname##_impl, METH_VARARGS);    \
    }                                                                          \
    static void                                                                \
    fnname(void **out_func, _HPy_CPyCFunction *out_trampoline)                 \
    {                                                                          \
        *out_func = fnname##_impl;                                             \
        *out_trampoline = fnname##_trampoline;                                 \
    }

#define METH_VARARGS  0x0001
#define METH_KEYWORDS 0x0002
/* METH_NOARGS and METH_O must not be combined with the flags above. */
#define METH_NOARGS   0x0004
#define METH_O        0x0008


#endif /* HPy_UNIVERSAL_H */
