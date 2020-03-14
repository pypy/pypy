import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator import cdir
from pypy import pypydir
from pypy.module.cpyext.cparser import CTypeSpace

PYPYDIR = py.path.local(pypydir)
BASE_DIR = PYPYDIR.join('module', '_hpy_universal', '_vendored')
INCLUDE_DIR = BASE_DIR.join('include')

eci = ExternalCompilationInfo(
    includes=["universal/hpy.h"],
    include_dirs=[
        cdir,        # for precommondefs.h
        INCLUDE_DIR, # for universal/hpy.h
    ],
    post_include_bits=["""
        // these are workarounds for a CTypeSpace limitation, since it can't properly
        // handle struct types which are not typedefs
        typedef struct _HPyContext_s _struct_HPyContext_s;
        typedef struct _HPy_s _struct_HPy_s;
    """],
)

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
    void * ctx_Number_Add;
    void * ctx_Err_SetString;
    void * ctx_Err_Occurred;
    void * ctx_Object_IsTrue;
    void * ctx_GetAttr;
    void * ctx_GetAttr_s;
    void * ctx_HasAttr;
    void * ctx_HasAttr_s;
    void * ctx_SetAttr;
    void * ctx_SetAttr_s;
    void * ctx_GetItem;
    void * ctx_GetItem_i;
    void * ctx_GetItem_s;
    void * ctx_SetItem;
    void * ctx_SetItem_i;
    void * ctx_SetItem_s;
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
    void * ctx_Dict_GetItem;
    void * ctx_FromPyObject;
    void * ctx_AsPyObject;
    void * ctx_CallRealFunctionFromTrampoline;
} _struct_HPyContext_s;
typedef struct _HPyContext_s *HPyContext;

typedef HPy (*HPyInitFunc)(HPyContext ctx);

typedef HPy (*HPyMeth_O)(HPyContext ctx, HPy self, HPy args);
typedef HPy (*HPyMeth_VarArgs)(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs);
typedef HPy (*HPyMeth_Keywords)(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs,
                                HPy kw);
typedef void *_HPyCPyCFunction; // not used here
typedef void (*_HPyMethodPairFunc)(HPyMeth_O *out_func,
                                   _HPyCPyCFunction *out_trampoline);


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
HPy_NULL = rffi.cast(HPy, 0)

HPyInitFunc = cts.gettype('HPyInitFunc')
_HPyCPyCFunction = cts.gettype('_HPyCPyCFunction')
HPyMeth_O = cts.gettype('HPyMeth_O')
HPyMeth_VarArgs = cts.gettype('HPyMeth_VarArgs')
HPyMeth_Keywords = cts.gettype('HPyMeth_Keywords')

HPyMethodDef = cts.gettype('HPyMethodDef')
HPyModuleDef = cts.gettype('HPyModuleDef')
# CTypeSpace converts "HPyMethodDef*" into lltype.Ptr(HPyMethodDef), but we
# want a CArrayPtr instead, so that we can index the items inside
# HPyModule_Create
HPyModuleDef._flds['c_m_methods'] = rffi.CArrayPtr(HPyMethodDef)

_HPy_METH = 0x100000
HPy_METH_VARARGS  = 0x0001 | _HPy_METH
HPy_METH_KEYWORDS = 0x0003 | _HPy_METH
HPy_METH_NOARGS   = 0x0004 | _HPy_METH
HPy_METH_O        = 0x0008 | _HPy_METH
