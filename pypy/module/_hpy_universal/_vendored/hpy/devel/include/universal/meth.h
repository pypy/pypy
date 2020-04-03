#ifndef HPY_UNIVERSAL_METH_H
#define HPY_UNIVERSAL_METH_H

/* in universal mode, an HPyMeth is a function which returns two output
 * arguments:
 *
 *     - the *_impl function
 *     - a trampoline which can be called by CPython
 *
 * In theory, the CPython trampoline is an implementation-specific detail of
 * the hpy.universal CPython module. However, it is too hard and unreliable to
 * generate them on the fly, and for the sake of simplicity it is easier to
 * just let the C compiler to generate it. This is done by the DEF macros.
 */
typedef void (*HPyMeth)(void **out_func, _HPy_CPyCFunction *out_trampoline);

/* ml_flags can be:
 *
 *   - METH_NOARGS, METH_O, etc: in this case ml_meth is interpreted as a legacy
 *     CPython function
 *
 *   - HPy_METH_NOARGS, etc: in this case ml_meth is interpreted as a new-style
 *     HPy function
 */
typedef struct {
    const char   *ml_name;   /* The name of the built-in function/method */
    HPyMeth      ml_meth;    /* see HPy_DEF_METH_*() */
    int          ml_flags;   /* Combination of METH_xxx flags, which mostly
                                describe the args expected by the C func */
    const char   *ml_doc;    /* The __doc__ attribute, or NULL */
} HPyMethodDef;

#define HPy_DECL_METH_NOARGS(fnname)                                    \
    void fnname(void **out_func, _HPy_CPyCFunction *out_trampoline);

#define HPy_DECL_METH_O(NAME) HPy_DECL_METH_NOARGS(NAME)
#define HPy_DECL_METH_VARARGS(NAME) HPy_DECL_METH_NOARGS(NAME)
#define HPy_DECL_METH_KEYWORDS(NAME) HPy_DECL_METH_NOARGS(NAME)


#define HPy_DEF_METH_NOARGS(fnname)                                            \
    static HPy fnname##_impl(HPyContext ctx, HPy self);                        \
    static struct _object *                                                    \
    fnname##_trampoline(struct _object *self, struct _object *noargs)          \
    {                                                                          \
        return _HPy_CallRealFunctionFromTrampoline(                            \
            _ctx_for_trampolines, self, NULL, NULL, fnname##_impl,             \
            HPy_METH_NOARGS);                                                  \
    }                                                                          \
    void                                                                       \
    fnname(void **out_func, _HPy_CPyCFunction *out_trampoline)                 \
    {                                                                          \
        *out_func = fnname##_impl;                                             \
        *out_trampoline = fnname##_trampoline;                                 \
    }

#define HPy_DEF_METH_O(fnname)                                                 \
    static HPy fnname##_impl(HPyContext ctx, HPy self, HPy arg);               \
    static struct _object *                                                    \
    fnname##_trampoline(struct _object *self, struct _object *arg)             \
    {                                                                          \
        return _HPy_CallRealFunctionFromTrampoline(                            \
            _ctx_for_trampolines, self, arg, NULL, fnname##_impl, HPy_METH_O); \
    }                                                                          \
    void                                                                       \
    fnname(void **out_func, _HPy_CPyCFunction *out_trampoline)                 \
    {                                                                          \
        *out_func = fnname##_impl;                                             \
        *out_trampoline = fnname##_trampoline;                                 \
    }

#define HPy_DEF_METH_VARARGS(fnname)                                           \
    static HPy fnname##_impl(HPyContext ctx, HPy self, HPy *args,              \
                             HPy_ssize_t nargs);                               \
    static struct _object *                                                    \
    fnname##_trampoline(struct _object *self, struct _object *args)            \
    {                                                                          \
        return _HPy_CallRealFunctionFromTrampoline(                            \
            _ctx_for_trampolines, self, args, NULL, fnname##_impl,             \
            HPy_METH_VARARGS);                                                 \
    }                                                                          \
    void                                                                       \
    fnname(void **out_func, _HPy_CPyCFunction *out_trampoline)                 \
    {                                                                          \
        *out_func = fnname##_impl;                                             \
        *out_trampoline = fnname##_trampoline;                                 \
    }

#define HPy_DEF_METH_KEYWORDS(fnname)                                          \
    static HPy fnname##_impl(HPyContext ctx, HPy self,                         \
                             HPy *args, HPy_ssize_t nargs, HPy kw);            \
    static struct _object *                                                    \
    fnname##_trampoline(struct _object *self, struct _object *args,            \
                        struct _object *kw)                                    \
    {                                                                          \
        return _HPy_CallRealFunctionFromTrampoline(                            \
            _ctx_for_trampolines, self, args, kw, fnname##_impl,               \
            HPy_METH_KEYWORDS);                                                \
    }                                                                          \
    void                                                                       \
    fnname(void **out_func, _HPy_CPyCFunction *out_trampoline)                 \
    {                                                                          \
        *out_func = fnname##_impl;                                             \
        *out_trampoline = (_HPy_CPyCFunction) fnname##_trampoline;             \
    }

// make sure to use a bit which is unused by CPython
#define _HPy_METH 0x100000
#define HPy_METH_VARARGS  (0x0001 | _HPy_METH)
#define HPy_METH_KEYWORDS (0x0003 | _HPy_METH)
/* METH_NOARGS and METH_O must not be combined with the flags above. */
#define HPy_METH_NOARGS   (0x0004 | _HPy_METH)
#define HPy_METH_O        (0x0008 | _HPy_METH)


#endif // HPY_UNIVERSAL_METH_H
