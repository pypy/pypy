import os
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


HPy = lltype.Signed
HPyContext = llmemory.Address

HPyInitFuncPtr = lltype.Ptr(lltype.FuncType([HPyContext], HPy))


# ----------------------------------------------------------------

# XXX temporary location
INCLUDE_DIR = os.path.join(os.path.dirname(__file__),
                           "test", "_vendored", "include")

eci = ExternalCompilationInfo(includes=["universal/hpy.h"],
                              include_dirs=[INCLUDE_DIR],
                              post_include_bits=["""

RPY_EXTERN void _HPy_FillFunction(int index, void *function);
RPY_EXTERN void *_HPy_GetGlobalCtx(void);
"""],
                              separate_module_sources=["""

struct _HPyRawContext_s {
    int ctx_version;
    void *ctx_raw_functions[1];
};

union _HPyContext_s_union {
    struct _HPyContext_s ctx;
    struct _HPyRawContext_s rawctx;
};

union _HPyContext_s_union hpy_global_ctx = {
    {
        .ctx_version = 1,
    }
};

void _HPy_FillFunction(int index, void *function)
{
    hpy_global_ctx.rawctx.ctx_raw_functions[index] = function;
}

void *_HPy_GetGlobalCtx(void)
{
    return &hpy_global_ctx;
}

"""])


_HPy_FillFunction = rffi.llexternal('_HPy_FillFunction',
                                    [rffi.INT_real, llmemory.Address],
                                    lltype.Void,
                                    compilation_info=eci, _nowrapper=True)

_HPy_GetGlobalCtx = rffi.llexternal('_HPy_GetGlobalCtx', [], HPyContext,
                                    compilation_info=eci, _nowrapper=True)
