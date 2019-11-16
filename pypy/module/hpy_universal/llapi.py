import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


HPy = lltype.Signed
HPyContext = rffi.VOIDP

HPyInitFuncPtr = lltype.Ptr(lltype.FuncType([HPyContext], HPy))

_HPyCFunctionPtr = lltype.Ptr(lltype.FuncType([HPyContext, HPy, HPy], HPy))
_HPy_CPyCFunctionPtr = rffi.VOIDP    # not used here

_HPyMethodPairFuncPtr = lltype.Ptr(lltype.FuncType([
        rffi.CArrayPtr(_HPyCFunctionPtr),
        rffi.CArrayPtr(_HPy_CPyCFunctionPtr)],
    lltype.Void))

HPyMethodDef = rffi.CStruct('HPyMethodDef',
    ('ml_name', rffi.CCHARP),
    ('ml_meth', _HPyMethodPairFuncPtr),
    ('ml_flags', rffi.INT_real),
    ('ml_doc', rffi.CCHARP),
)

HPyModuleDef = rffi.CStruct('HPyModuleDef',
    ('dummy', rffi.VOIDP),
    ('m_name', rffi.CCHARP),
    ('m_doc', rffi.CCHARP),
    ('m_size', lltype.Signed),
    ('m_methods', rffi.CArrayPtr(HPyMethodDef)),
)


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
                                    [rffi.INT_real, rffi.VOIDP],
                                    lltype.Void,
                                    compilation_info=eci, _nowrapper=True)

_HPy_GetGlobalCtx = rffi.llexternal('_HPy_GetGlobalCtx', [], HPyContext,
                                    compilation_info=eci, _nowrapper=True)
