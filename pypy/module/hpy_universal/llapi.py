import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from pypy import pypydir
from pypy.module.hpy_universal import _vendored

PYPYDIR = py.path.local(pypydir)
INCLUDE_DIR = PYPYDIR.join('module', 'hpy_universal', '_vendored', 'include')
SRC_DIR = PYPYDIR.join('module', 'hpy_universal', 'src')

# XXX I don't understand what is going on here: if I put getargs.c as
# separate_module_files, then ll2ctypes can't find it. I need to #include t in
# separate_module_sources for now...
eci = ExternalCompilationInfo(includes=["universal/hpy.h"],
                              include_dirs=[INCLUDE_DIR],
                              ## separate_module_files=[
                              ##     SRC_DIR.join('getargs.c'),
                              ##     ],
                              post_include_bits=["""
RPY_EXTERN void *_HPy_GetGlobalCtx(void);
RPY_EXTERN int ctx_Arg_Parse(HPyContext ctx, HPy *args, HPy_ssize_t nargs,
                             const char *fmt, va_list vl);
"""],
                              separate_module_sources=["""

#include "%s"

struct _HPyContext_s hpy_global_ctx;
void *_HPy_GetGlobalCtx(void)
{
    return &hpy_global_ctx;
}

""" % SRC_DIR.join('getargs.c')])

HPy_ssize_t = lltype.Signed # XXXXXXXXX?

# for practical reason, we use a primitive type to represent HPy almost
# everywhere in RPython. HOWEVER, the "real" HPy C type which is defined in
# universal/hpy.h is an anonymous struct: we need to use it e.g. to represent
# fields inside HPyContextS
HPy = HPy_ssize_t
HPyS_real = rffi.CStruct('HPy',
    ('_i', HPy_ssize_t),
    hints={'eci': eci, 'typedef': True},
)


HPyContextS = rffi.CStruct('_HPyContext_s',
    ('ctx_version', rffi.INT_real),
    ('h_None', HPyS_real),
    ('h_True', HPyS_real),
    ('h_False', HPyS_real),
    ('h_ValueError', HPyS_real),
    ('ctx_Module_Create', rffi.VOIDP),
    ('ctx_Dup', rffi.VOIDP),
    ('ctx_Close', rffi.VOIDP),
    ('ctx_Long_FromLong', rffi.VOIDP),
    ('ctx_Long_AsLong', rffi.VOIDP),
    ('ctx_Arg_Parse', rffi.VOIDP),
    ('ctx_Number_Add', rffi.VOIDP),
    ('ctx_Unicode_FromString', rffi.VOIDP),
    ('ctx_Err_SetString', rffi.VOIDP),
    ('ctx_FromPyObject', rffi.VOIDP),
    ('ctx_AsPyObject', rffi.VOIDP),
    ('ctx_CallRealFunctionFromTrampoline', rffi.VOIDP),
    hints={'eci': eci},
)
HPyContext = lltype.Ptr(HPyContextS)
HPyInitFuncPtr = lltype.Ptr(lltype.FuncType([HPyContext], HPy))

_HPyCFunctionPtr = lltype.Ptr(lltype.FuncType([HPyContext, HPy, HPy], HPy))
_HPy_CPyCFunctionPtr = rffi.VOIDP    # not used here

HPyMeth_VarArgs = lltype.Ptr(
    lltype.FuncType([HPyContext, HPy, lltype.Ptr(rffi.CArray(HPy)), HPy_ssize_t], HPy))


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

# NOTE: this is not the real signature (we don't know what to put for
# va_list), but it's good enough to get the address of the function to store
# in the ctx. DO NOT CALL THIS!. TO avoid possible mistakes, we directly cast
# it to VOIDP
ctx_Arg_Parse_fn = rffi.llexternal('ctx_Arg_Parse', [], rffi.INT_real,
                                compilation_info=eci, _nowrapper=True)
ctx_Arg_Parse = rffi.cast(rffi.VOIDP, ctx_Arg_Parse_fn)
