#ifndef HPY_UNIVERSAL_MODULE_H
#define HPY_UNIVERSAL_MODULE_H

// this is defined by HPy_MODINIT
extern HPyContext _ctx_for_trampolines;

#define HPyModuleDef_HEAD_INIT NULL

typedef struct {
    void *dummy; // this is needed because we put a comma after HPyModuleDef_HEAD_INIT :(
    const char* m_name;
    const char* m_doc;
    HPy_ssize_t m_size;
    HPyMethodDef *m_methods;
} HPyModuleDef;


#define HPy_MODINIT(modname)                                   \
    _HPy_HIDDEN HPyContext _ctx_for_trampolines;               \
    static HPy init_##modname##_impl(HPyContext ctx);          \
    HPy HPyInit_##modname(HPyContext ctx)                      \
    {                                                          \
        _ctx_for_trampolines = ctx;                            \
        return init_##modname##_impl(ctx);                     \
    }

#endif // HPY_UNIVERSAL_MODULE_H
