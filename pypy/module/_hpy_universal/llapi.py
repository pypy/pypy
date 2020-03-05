import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator import cdir
from pypy import pypydir
from pypy.module.cpyext.cparser import CTypeSpace

PYPYDIR = py.path.local(pypydir)
INCLUDE_DIR = PYPYDIR.join('module', '_hpy_universal', '_vendored', 'include')
SRC_DIR = PYPYDIR.join('module', '_hpy_universal', 'src')


eci = ExternalCompilationInfo(
    includes=["universal/hpy.h", "hpyarg.h"],
    include_dirs=[
        cdir,        # for precommondefs.h
        INCLUDE_DIR, # for universal/hpy.h
        SRC_DIR,     # for hpyarg.h
    ],
    separate_module_files=[
        SRC_DIR.join('hpyarg.c'),
    ],
    post_include_bits=["""
        RPY_EXTERN void *_HPy_GetGlobalCtx(void);

        // these are workarounds for a CTypeSpace limitation, since it can't properly
        // handle struct types which are not typedefs
        typedef struct _HPyContext_s _struct_HPyContext_s;
        typedef struct _HPy_s _struct_HPy_s;
    """],
    separate_module_sources=["""
        struct _HPyContext_s hpy_global_ctx;
        void *_HPy_GetGlobalCtx(void)
        {
            return &hpy_global_ctx;
        }
    """])

cts = CTypeSpace()
# NOTE: the following C source is NOT seen by the C compiler during
# translation: it is used only as a nice way to declare the lltype.* types
# which are needed here
cts.headers.append('stdint.h')
cts.parse_source("""
typedef intptr_t HPy_ssize_t;

// see below for more info about HPy vs _struct_HPy_s
typedef struct _HPy_s {
    HPy_ssize_t _i;
} _struct_HPy_s;
typedef HPy_ssize_t HPy;

typedef struct _HPyContext_s {
    int ctx_version;
    struct _HPy_s h_None;
    struct _HPy_s h_True;
    struct _HPy_s h_False;
    struct _HPy_s h_ValueError;
    struct _HPy_s h_TypeError;
    void * ctx_Module_Create;
    void * ctx_Dup;
    void * ctx_Close;
    void * ctx_Long_FromLong;
    void * ctx_Long_FromLongLong;
    void * ctx_Long_FromUnsignedLongLong;
    void * ctx_Long_AsLong;
    void * ctx_Float_FromDouble;
    void * ctx_Arg_Parse;
    void * ctx_Number_Add;
    void * ctx_Err_SetString;
    void * ctx_Bytes_Check;
    void * ctx_Bytes_Size;
    void * ctx_Bytes_GET_SIZE;
    void * ctx_Bytes_AsString;
    void * ctx_Bytes_AS_STRING;
    void * ctx_Unicode_FromString;
    void * ctx_Unicode_Check;
    void * ctx_Unicode_AsUTF8String;
    void * ctx_Unicode_FromWideChar;
    void * ctx_List_New;
    void * ctx_List_Append;
    void * ctx_Dict_New;
    void * ctx_Dict_SetItem;
    void * ctx_FromPyObject;
    void * ctx_AsPyObject;
    void * ctx_CallRealFunctionFromTrampoline;
} _struct_HPyContext_s;
typedef struct _HPyContext_s *HPyContext;

typedef HPy (*HPyInitFunc)(HPyContext ctx);

typedef HPy (*_HPyCFunction)(HPyContext ctx, HPy self, HPy args);
typedef void *_HPyCPyCFunction; // not used here
typedef void (*_HPyMethodPairFunc)(_HPyCFunction *out_func,
                                   _HPyCPyCFunction *out_trampoline);
typedef HPy (*HPyMeth_VarArgs)(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs);

typedef struct {
    const char         *ml_name;
    _HPyMethodPairFunc ml_meth;
    int                ml_flags;
    const char         *ml_doc;
} HPyMethodDef;

typedef struct {
    void *dummy; // this is needed because we put a comma after HPyModuleDef_HEAD_INIT :(
    const char* m_name;
    const char* m_doc;
    HPy_ssize_t m_size;
    HPyMethodDef *m_methods;
} HPyModuleDef;
""")

HPy_ssize_t = cts.gettype('HPy_ssize_t')
# XXX: HPyContext is equivalent to the old HPyContext which was defined
# explicitly using rffi.CStruct: the only different is that this is missing
# hints={'eci': eci}: however, the tests still pass (including
# ztranslation). Why was the eci needed?
HPyContext = cts.gettype('HPyContext')

# for practical reason, we use a primitive type to represent HPy almost
# everywhere in RPython: for example, rffi cannot handle functions returning
# structs. HOWEVER, the "real" HPy C type is a struct, which is available as
# "_struct_HPy_s"
HPy = cts.gettype('HPy')

HPyInitFunc = cts.gettype('HPyInitFunc')
_HPyCFunction = cts.gettype('_HPyCFunction')
_HPyCPyCFunction = cts.gettype('_HPyCPyCFunction')
HPyMeth_VarArgs = cts.gettype('HPyMeth_VarArgs')

HPyMethodDef = cts.gettype('HPyMethodDef')
HPyModuleDef = cts.gettype('HPyModuleDef')
# CTypeSpace converts "HPyMethodDef*" into lltype.Ptr(HPyMethodDef), but we
# want a CArrayPtr instead, so that we can index the items inside
# HPyModule_Create
HPyModuleDef._flds['c_m_methods'] = rffi.CArrayPtr(HPyMethodDef)

_HPy_METH = 0x100000
HPy_METH_VARARGS  = 0x0001 | _HPy_METH
HPy_METH_KEYWORDS = 0x0002 | _HPy_METH
HPy_METH_NOARGS   = 0x0004 | _HPy_METH
HPy_METH_O        = 0x0008 | _HPy_METH

# ----------------------------------------------------------------

_HPy_GetGlobalCtx = rffi.llexternal('_HPy_GetGlobalCtx', [], HPyContext,
                                    compilation_info=eci, _nowrapper=True)

# NOTE: this is not the real signature (we don't know what to put for
# va_list), but it's good enough to get the address of the function to store
# in the ctx. DO NOT CALL THIS!
DONT_CALL_ctx_Arg_Parse = rffi.llexternal('ctx_Arg_Parse', [], rffi.INT_real,
                                          compilation_info=eci, _nowrapper=True)
