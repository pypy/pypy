import py, os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.objectmodel import specialize
from rpython.tool.cparser import CTypeSpace


src_dir = py.path.local(os.path.dirname(__file__)) / 'src'

eci = ExternalCompilationInfo(
    includes = ['parse_c_type.h'],
    separate_module_files = [src_dir / 'parse_c_type.c'],
    include_dirs = [src_dir, cdir],
    pre_include_bits = ['#define _CFFI_INTERNAL'],
)

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           _nowrapper=True, **kwds)

_CFFI_OPCODE_T = rffi.VOIDP
cts = CTypeSpace()
INCLUDE_DIR = os.path.join(os.path.dirname(__file__), 'src')
with open(os.path.join(INCLUDE_DIR, 'parse_c_type.h')) as fid:
    data = fid.read()
    end = data.find("#ifdef _CFFI_INTERNAL")
    cts.parse_source(data[:end])

GLOBAL_S = cts.gettype('struct _cffi_global_s')
CDL_INTCONST_S = lltype.Struct('cdl_intconst_s',
                       ('value', rffi.ULONGLONG),
                       ('neg', rffi.INT))
STRUCT_UNION_S = cts.gettype('struct _cffi_struct_union_s')
FIELD_S = cts.gettype('struct _cffi_field_s')
ENUM_S = cts.gettype('struct _cffi_enum_s')
TYPENAME_S = cts.gettype('struct _cffi_typename_s')
PCTX = lltype.Ptr(cts.gettype('struct _cffi_type_context_s'))
PINFO = lltype.Ptr(cts.gettype('struct _cffi_parse_info_s'))
PEXTERNPY = lltype.Ptr(cts.gettype('struct _cffi_externpy_s'))
GETCONST_S = cts.gettype('struct _cffi_getconst_s')

ll_parse_c_type = llexternal('pypy_parse_c_type', [PINFO, rffi.CCHARP],
                             rffi.INT)
ll_search_in_globals = llexternal('pypy_search_in_globals',
                                  [PCTX, rffi.CCHARP, rffi.SIZE_T],
                                  rffi.INT)
ll_search_in_struct_unions = llexternal('pypy_search_in_struct_unions',
                                        [PCTX, rffi.CCHARP, rffi.SIZE_T],
                                        rffi.INT)
ll_set_cdl_realize_global_int = llexternal('pypy_set_cdl_realize_global_int',
                                           [lltype.Ptr(GLOBAL_S)],
                                           lltype.Void)
ll_enum_common_types = llexternal('pypy_enum_common_types',
                                  [rffi.INT], rffi.CCHARP)

def parse_c_type(info, input):
    with rffi.scoped_view_charp(input) as p_input:
        res = ll_parse_c_type(info, p_input)
    return rffi.cast(lltype.Signed, res)

NULL_CTX = lltype.nullptr(PCTX.TO)
FFI_COMPLEXITY_OUTPUT = 1200     # xxx should grow as needed
internal_output = lltype.malloc(rffi.VOIDPP.TO, FFI_COMPLEXITY_OUTPUT,
                                flavor='raw', zero=True, immortal=True)
CTXOBJ = lltype.Struct('cffi_ctxobj',
                                   ('ctx', PCTX.TO),
                                   ('info', PINFO.TO))

def allocate_ctxobj(src_ctx):
    p = lltype.malloc(CTXOBJ, flavor='raw', zero=True)
    if src_ctx:
        rffi.c_memcpy(rffi.cast(rffi.VOIDP, p.ctx),
                      rffi.cast(rffi.CONST_VOIDP, src_ctx),
                      rffi.cast(rffi.SIZE_T, rffi.sizeof(PCTX.TO)))
    p.info.c_ctx = p.ctx
    p.info.c_output = internal_output
    rffi.setintfield(p.info, 'c_output_size', FFI_COMPLEXITY_OUTPUT)
    return p

def free_ctxobj(p):
    lltype.free(p, flavor='raw')

def get_num_types(src_ctx):
    return rffi.getintfield(src_ctx, 'c_num_types')

def search_in_globals(ctx, name):
    with rffi.scoped_view_charp(name) as c_name:
        result = ll_search_in_globals(ctx, c_name,
                                      rffi.cast(rffi.SIZE_T, len(name)))
    return rffi.cast(lltype.Signed, result)

def search_in_struct_unions(ctx, name):
    with rffi.scoped_view_charp(name) as c_name:
        result = ll_search_in_struct_unions(ctx, c_name,
                                            rffi.cast(rffi.SIZE_T, len(name)))
    return rffi.cast(lltype.Signed, result)
