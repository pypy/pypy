import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator import cdir
from pypy import pypydir
from pypy.module.cpyext.cparser import CTypeSpace

PYPYDIR = py.path.local(pypydir)
SRC_DIR = PYPYDIR.join('module', '_hpy_universal', 'src')
BASE_DIR = PYPYDIR.join('module', '_hpy_universal', '_vendored', 'hpy', 'devel')
INCLUDE_DIR = BASE_DIR.join('include')

eci = ExternalCompilationInfo(
    compile_extra = ["-DHPY_UNIVERSAL_ABI"],
    includes=["universal/hpy.h", "hpyerr.h", "rffi_hacks.h"],
    include_dirs=[
        cdir,        # for precommondefs.h
        INCLUDE_DIR, # for universal/hpy.h
        SRC_DIR,     # for hpyerr.h
    ],
    separate_module_files=[
        SRC_DIR.join('bridge.c'),
        SRC_DIR.join('hpyerr.c'),
    ],
    post_include_bits=["""
        // these are workarounds for a CTypeSpace limitation, since it can't properly
        // handle struct types which are not typedefs
        typedef struct _HPyContext_s _struct_HPyContext_s;
        typedef struct _HPy_s _struct_HPy_s;
        typedef struct _HPyObject_head_s _struct_HPyObject_head_s;
    """],
)

cts = CTypeSpace()
cts.headers.append('stdint.h')
cts.parse_source(INCLUDE_DIR.join('common', 'autogen_hpyslot.h').read())

# NOTE: the following C source is NOT seen by the C compiler during
# translation: it is used only as a nice way to declare the lltype.* types
# which are needed here
cts.parse_source("""
typedef intptr_t HPy_ssize_t;
typedef intptr_t HPy_hash_t;

// see below for more info about HPy vs _struct_HPy_s
typedef struct _HPy_s {
    HPy_ssize_t _i;
} _struct_HPy_s;
typedef HPy_ssize_t HPy;

typedef struct _HPyListBuilder_s {
    HPy_ssize_t _lst;
} _struct_HPyListBuilder_s;
typedef HPy_ssize_t HPyListBuilder;

typedef struct _HPyTupleBuilder_s {
    HPy_ssize_t _lst;
} _struct_HPyTupleBuilder_s;
typedef HPy_ssize_t HPyTupleBuilder;

typedef struct _HPyTracker_s {
    HPy_ssize_t _i;
} _struct_HPyTracker_s;
typedef HPy_ssize_t HPyTracker;

typedef struct _HPyContext_s {
    int ctx_version;
    struct _HPy_s h_None;
    struct _HPy_s h_True;
    struct _HPy_s h_False;
    struct _HPy_s h_Exception;
    struct _HPy_s h_ValueError;
    struct _HPy_s h_TypeError;
    struct _HPy_s h_IndexError;
    struct _HPy_s h_BaseObjectType;
    struct _HPy_s h_TypeType;
    struct _HPy_s h_LongType;
    struct _HPy_s h_UnicodeType;
    struct _HPy_s h_TupleType;
    struct _HPy_s h_ListType;
    void * ctx_Module_Create;
    void * ctx_Dup;
    void * ctx_Close;
    void * ctx_Long_FromLong;
    void * ctx_Long_FromUnsignedLong;
    void * ctx_Long_FromLongLong;
    void * ctx_Long_FromUnsignedLongLong;
    void * ctx_Long_FromSize_t;
    void * ctx_Long_FromSsize_t;
    void * ctx_Long_AsLong;
    void * ctx_Float_FromDouble;
    void * ctx_Float_AsDouble;
    void * ctx_Length;
    void * ctx_Number_Check;
    void * ctx_Add;
    void * ctx_Subtract;
    void * ctx_Multiply;
    void * ctx_MatrixMultiply;
    void * ctx_FloorDivide;
    void * ctx_TrueDivide;
    void * ctx_Remainder;
    void * ctx_Divmod;
    void * ctx_Power;
    void * ctx_Negative;
    void * ctx_Positive;
    void * ctx_Absolute;
    void * ctx_Invert;
    void * ctx_Lshift;
    void * ctx_Rshift;
    void * ctx_And;
    void * ctx_Xor;
    void * ctx_Or;
    void * ctx_Index;
    void * ctx_Long;
    void * ctx_Float;
    void * ctx_InPlaceAdd;
    void * ctx_InPlaceSubtract;
    void * ctx_InPlaceMultiply;
    void * ctx_InPlaceMatrixMultiply;
    void * ctx_InPlaceFloorDivide;
    void * ctx_InPlaceTrueDivide;
    void * ctx_InPlaceRemainder;
    void * ctx_InPlacePower;
    void * ctx_InPlaceLshift;
    void * ctx_InPlaceRshift;
    void * ctx_InPlaceAnd;
    void * ctx_InPlaceXor;
    void * ctx_InPlaceOr;
    void * ctx_Err_SetString;
    void * ctx_Err_Occurred;
    void * ctx_Err_NoMemory;
    void * ctx_IsTrue;
    void * ctx_Type_FromSpec;
    void * ctx_Type_GenericNew;
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
    void * ctx_Cast;
    void * ctx_New;
    void * ctx_Repr;
    void * ctx_Str;
    void * ctx_ASCII;
    void * ctx_Bytes;
    void * ctx_RichCompare;
    void * ctx_RichCompareBool;
    void * ctx_Hash;
    void * ctx_Bytes_Check;
    void * ctx_Bytes_Size;
    void * ctx_Bytes_GET_SIZE;
    void * ctx_Bytes_AsString;
    void * ctx_Bytes_AS_STRING;
    void * ctx_Unicode_FromString;
    void * ctx_Unicode_Check;
    void * ctx_Unicode_AsUTF8String;
    void * ctx_Unicode_FromWideChar;
    void * ctx_List_Check;
    void * ctx_List_New;
    void * ctx_List_Append;
    void * ctx_Dict_Check;
    void * ctx_Dict_New;
    void * ctx_Dict_SetItem;
    void * ctx_Dict_GetItem;
    void * ctx_FatalError;
    void * ctx_Tuple_FromArray;
    void * ctx_FromPyObject;
    void * ctx_AsPyObject;
    void * ctx_CallRealFunctionFromTrampoline;
    void * ctx_CallDestroyAndThenDealloc;
    void * ctx_ListBuilder_New;
    void * ctx_ListBuilder_Set;
    void * ctx_ListBuilder_Build;
    void * ctx_ListBuilder_Cancel;
    void * ctx_TupleBuilder_New;
    void * ctx_TupleBuilder_Set;
    void * ctx_TupleBuilder_Build;
    void * ctx_TupleBuilder_Cancel;
    void * ctx_Tracker_New;
    void * ctx_Tracker_Add;
    void * ctx_Tracker_RemoveAll;
    void * ctx_Tracker_Free;
} _struct_HPyContext_s;

typedef struct _HPyContext_s *HPyContext;

typedef HPy (*HPyInitFunc)(HPyContext ctx);
typedef int HPyFunc_Signature;

/* hpydef.h */

typedef struct {
    HPySlot_Slot slot;     // The slot to fill
    void *impl;            // Function pointer to the implementation
    void *cpy_trampoline;  // Used by CPython to call impl
} HPySlot;

typedef struct {
    const char *name;             // The name of the built-in function/method
    const char *doc;              // The __doc__ attribute, or NULL
    void *impl;                   // Function pointer to the implementation
    void *cpy_trampoline;         // Used by CPython to call impl
    HPyFunc_Signature signature;  // Indicates impl's expected the signature
} HPyMeth;

typedef enum {
    HPyMember_SHORT = 0,
    HPyMember_INT = 1,
    HPyMember_LONG = 2,
    HPyMember_FLOAT = 3,
    HPyMember_DOUBLE = 4,
    HPyMember_STRING = 5,
    HPyMember_OBJECT = 6,
    HPyMember_CHAR = 7,   /* 1-character string */
    HPyMember_BYTE = 8,   /* 8-bit signed int */
    /* unsigned variants: */
    HPyMember_UBYTE = 9,
    HPyMember_USHORT = 10,
    HPyMember_UINT = 11,
    HPyMember_ULONG = 12,

    /* Added by Jack: strings contained in the structure */
    HPyMember_STRING_INPLACE = 13,

    /* Added by Lillo: bools contained in the structure (assumed char) */
    HPyMember_BOOL = 14,
    HPyMember_OBJECT_EX = 16,  /* Like T_OBJECT, but raises AttributeError
                                  when the value is NULL, instead of
                                  converting to None. */
    HPyMember_LONGLONG = 17,
    HPyMember_ULONGLONG = 18,

    HPyMember_HPYSSIZET = 19,  /* HPy_ssize_t */
    HPyMember_NONE = 20,       /* Value is always None */

} HPyMember_FieldType;

typedef struct {
    const char *name;
    HPyMember_FieldType type;
    HPy_ssize_t offset;
    int readonly;
    const char *doc;
} HPyMember;

typedef struct {
    const char *name;
    void *getter_impl;            // Function pointer to the implementation
    void *setter_impl;            // Same; this may be NULL
    void *getter_cpy_trampoline;  // Used by CPython to call getter_impl
    void *setter_cpy_trampoline;  // Same; this may be NULL
    const char *doc;
    void *closure;
} HPyGetSet;

typedef enum {
    HPyDef_Kind_Slot = 1,
    HPyDef_Kind_Meth = 2,
    HPyDef_Kind_Member = 3,
    HPyDef_Kind_GetSet = 4,
} HPyDef_Kind;

typedef struct {
    HPyDef_Kind kind;
    //union {
    //    HPySlot slot;
        HPyMeth meth;
        // HPyMember member;
        // HPyGetSet getset;
    //};
} HPyDef;

// work around rffi's lack of support for unions
typedef struct {
    HPyDef_Kind kind;
    HPySlot slot;
} _pypy_HPyDef_as_slot;

typedef struct {
    HPyDef_Kind kind;
    HPyMember member;
} _pypy_HPyDef_as_member;

typedef struct {
    HPyDef_Kind kind;
    HPyGetSet getset;
} _pypy_HPyDef_as_getset;


/* hpymodule.h */

typedef void cpy_PyMethodDef;

typedef struct {
    void *dummy; // this is needed because we put a comma after HPyModuleDef_HEAD_INIT :(
    const char* m_name;
    const char* m_doc;
    HPy_ssize_t m_size;
    cpy_PyMethodDef *legacy_methods;
    HPyDef **defines;
} HPyModuleDef;

/* hpytype.h */

typedef struct _HPyObject_head_s {
    HPy_ssize_t _reserved0;
    void *_reserved1;
} _struct_HPyObject_head_s;

typedef struct {
    const char* name;
    int basicsize;
    int itemsize;
    unsigned int flags;
    void *legacy_slots; // PyType_Slot *
    HPyDef **defines;   /* points to an array of 'HPyDef *' */
} HPyType_Spec;

typedef enum {
    HPyType_SpecParam_Base = 1,
    HPyType_SpecParam_BasesTuple = 2,
    //HPyType_SpecParam_Metaclass = 3,
    //HPyType_SpecParam_Module = 4,
} HPyType_SpecParam_Kind;

typedef struct {
    HPyType_SpecParam_Kind kind;
    struct _HPy_s object;
} HPyType_SpecParam;

/* All types are dynamically allocated */
#define _Py_TPFLAGS_HEAPTYPE (1UL << 9)

/* Set if the type allows subclassing */
#define HPy_TPFLAGS_BASETYPE (1UL << 10)
#define HPy_TPFLAGS_DEFAULT _Py_TPFLAGS_HEAPTYPE


/* Rich comparison opcodes */
#define HPy_LT 0
#define HPy_LE 1
#define HPy_EQ 2
#define HPy_NE 3
#define HPy_GT 4
#define HPy_GE 5

/* autogen_hpyfunc_declare.h */

typedef HPy (*HPyFunc_noargs)(HPyContext ctx, HPy self);
typedef HPy (*HPyFunc_o)(HPyContext ctx, HPy self, HPy arg);
typedef HPy (*HPyFunc_varargs)(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs);
typedef HPy (*HPyFunc_keywords)(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs, HPy kw);
typedef HPy (*HPyFunc_unaryfunc)(HPyContext ctx, HPy);
typedef HPy (*HPyFunc_binaryfunc)(HPyContext ctx, HPy, HPy);
typedef HPy (*HPyFunc_ternaryfunc)(HPyContext ctx, HPy, HPy, HPy);
typedef int (*HPyFunc_inquiry)(HPyContext ctx, HPy);
typedef HPy_ssize_t (*HPyFunc_lenfunc)(HPyContext ctx, HPy);
typedef HPy (*HPyFunc_ssizeargfunc)(HPyContext ctx, HPy, HPy_ssize_t);
typedef HPy (*HPyFunc_ssizessizeargfunc)(HPyContext ctx, HPy, HPy_ssize_t, HPy_ssize_t);
typedef int (*HPyFunc_ssizeobjargproc)(HPyContext ctx, HPy, HPy_ssize_t, HPy);
typedef int (*HPyFunc_ssizessizeobjargproc)(HPyContext ctx, HPy, HPy_ssize_t, HPy_ssize_t, HPy);
typedef int (*HPyFunc_objobjargproc)(HPyContext ctx, HPy, HPy, HPy);
typedef void (*HPyFunc_freefunc)(HPyContext ctx, void *);
typedef HPy (*HPyFunc_getattrfunc)(HPyContext ctx, HPy, char *);
typedef HPy (*HPyFunc_getattrofunc)(HPyContext ctx, HPy, HPy);
typedef int (*HPyFunc_setattrfunc)(HPyContext ctx, HPy, char *, HPy);
typedef int (*HPyFunc_setattrofunc)(HPyContext ctx, HPy, HPy, HPy);
typedef HPy (*HPyFunc_reprfunc)(HPyContext ctx, HPy);
typedef HPy_hash_t (*HPyFunc_hashfunc)(HPyContext ctx, HPy);
typedef HPy (*HPyFunc_richcmpfunc)(HPyContext ctx, HPy, HPy, int);
typedef HPy (*HPyFunc_getiterfunc)(HPyContext ctx, HPy);
typedef HPy (*HPyFunc_iternextfunc)(HPyContext ctx, HPy);
typedef HPy (*HPyFunc_descrgetfunc)(HPyContext ctx, HPy, HPy, HPy);
typedef int (*HPyFunc_descrsetfunc)(HPyContext ctx, HPy, HPy, HPy);
typedef int (*HPyFunc_initproc)(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs, HPy kw);
typedef HPy (*HPyFunc_getter)(HPyContext ctx, HPy, void *);
typedef int (*HPyFunc_setter)(HPyContext ctx, HPy, HPy, void *);
typedef int (*HPyFunc_objobjproc)(HPyContext ctx, HPy, HPy);
typedef void (*HPyFunc_destroyfunc)(void *);
""")

# HACK! We manually assign _hints['eci'] to ensure that the eci is included in
# the translation, else common_header.h does not include hpy.h. A more proper
# solution probably involves telling CTypeSpace which eci the types come from?
HPyContext = cts.gettype('HPyContext')
HPyContext.TO._hints['eci'] = eci

HPy_ssize_t = cts.gettype('HPy_ssize_t')

# for practical reason, we use a primitive type to represent HPy almost
# everywhere in RPython: for example, rffi cannot handle functions returning
# structs. HOWEVER, the "real" HPy C type is a struct, which is available as
# "_struct_HPy_s"
HPy = cts.gettype('HPy')
HPy_NULL = rffi.cast(HPy, 0)

HPyInitFunc = cts.gettype('HPyInitFunc')

cpy_PyMethodDef = cts.gettype('cpy_PyMethodDef')
HPyModuleDef = cts.gettype('HPyModuleDef')
# CTypeSpace converts "PyMethodDef*" into lltype.Ptr(PyMethodDef), but we
# want a CArrayPtr instead, so that we can index the items inside
# HPyModule_Create
HPyModuleDef._flds['c_legacy_methods'] = rffi.CArrayPtr(cpy_PyMethodDef)

# enum HPyFunc_Signature {
HPyFunc_VARARGS  = 1
HPyFunc_KEYWORDS = 2
HPyFunc_NOARGS   = 3
HPyFunc_O        = 4
# ...
# }

HPyType_SpecParam_Kind = cts.gettype('HPyType_SpecParam_Kind')

HPy_LT = 0
HPy_LE = 1
HPy_EQ = 2
HPy_NE = 3
HPy_GT = 4
HPy_GE = 5

SIZEOF_HPyObject_HEAD = rffi.sizeof(cts.gettype('struct _HPyObject_head_s'))

# HPy API functions which are implemented directly in C
pypy_HPyErr_Occurred = rffi.llexternal('pypy_HPyErr_Occurred', [HPyContext],
                                       rffi.INT_real,
                                       compilation_info=eci, _nowrapper=True)

pypy_HPyErr_SetString = rffi.llexternal('pypy_HPyErr_SetString',
                                        [HPyContext, HPy, rffi.CCHARP],
                                        lltype.Void,
                                        compilation_info=eci, _nowrapper=True)
