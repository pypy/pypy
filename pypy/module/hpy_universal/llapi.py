import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from pypy.module.hpy_universal import _vendored

INCLUDE_DIR = str(py.path.local(_vendored.__file__).dirpath().join('include'))
eci = ExternalCompilationInfo(includes=["universal/hpy.h"],
                              include_dirs=[INCLUDE_DIR],
                              post_include_bits=["""
RPY_EXTERN void *_HPy_GetGlobalCtx(void);
"""],
                              separate_module_sources=["""

struct _HPyContext_s hpy_global_ctx;
void *_HPy_GetGlobalCtx(void)
{
    return &hpy_global_ctx;
}

"""])


HPy = lltype.Signed
HPyContextS = rffi.CStruct('_HPyContext_s',
    ('ctx_version', rffi.INT_real),
    ('ctx_Module_Create', rffi.VOIDP),
    ('ctx_None_Get', rffi.VOIDP),
    ('ctx_Dup', rffi.VOIDP),
    ('ctx_Close', rffi.VOIDP),
    ('ctx_Long_FromLong', rffi.VOIDP),
    ('ctx_Long_AsLong', rffi.VOIDP),
    ('ctx_Arg_ParseTuple', rffi.VOIDP),
    ('ctx_Number_Add', rffi.VOIDP),
    ('ctx_Unicode_FromString', rffi.VOIDP),
    ('ctx_FromPyObject', rffi.VOIDP),
    ('ctx_AsPyObject', rffi.VOIDP),
    ('ctx_CallRealFunctionFromTrampoline', rffi.VOIDP),
    hints={'eci': eci},
)
HPyContext = lltype.Ptr(HPyContextS)

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
    hints={'eci': eci, 'typedef': True},
)

HPyModuleDef = rffi.CStruct('HPyModuleDef',
    ('dummy', rffi.VOIDP),
    ('m_name', rffi.CCHARP),
    ('m_doc', rffi.CCHARP),
    ('m_size', lltype.Signed),
    ('m_methods', rffi.CArrayPtr(HPyMethodDef)),
    hints={'eci': eci, 'typedef': True},
)

METH_VARARGS  = 0x0001
METH_KEYWORDS = 0x0002
METH_NOARGS   = 0x0004
METH_O        = 0x0008


# ----------------------------------------------------------------


_HPy_GetGlobalCtx = rffi.llexternal('_HPy_GetGlobalCtx', [], HPyContext,
                                    compilation_info=eci, _nowrapper=True)
