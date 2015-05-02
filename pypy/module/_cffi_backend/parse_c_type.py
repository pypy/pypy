import py, os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo


src_dir = py.path.local(os.path.dirname(__file__)) / 'src'

eci = ExternalCompilationInfo(
    includes = ['parse_c_type.h'],
    separate_module_files = [src_dir / 'parse_c_type.c'],
    include_dirs = [src_dir, cdir],
    pre_include_bits = ['#define _CFFI_INTERNAL'],
)

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci, **kwds)


GLOBAL_S = rffi.CStruct('struct _cffi_global_s')
STRUCT_UNION_S = rffi.CStruct('struct _cffi_struct_union_s',
                       ('name', rffi.CCHARP),
                       ('type_index', rffi.INT),
                       ('flags', rffi.INT),
                       ('size', rffi.SIZE_T),
                       ('alignment', rffi.INT),
                       ('first_field_index', rffi.INT),
                       ('num_fields', rffi.INT))
FIELD_S = rffi.CStruct('struct _cffi_field_s')
ENUM_S = rffi.CStruct('struct _cffi_enum_s',
                       ('name', rffi.CCHARP),
                       ('type_index', rffi.INT),
                       ('type_prim', rffi.INT),
                       ('enumerators', rffi.CCHARP))
TYPENAME_S = rffi.CStruct('struct _cffi_typename_s')

PCTX = rffi.CStructPtr('struct _cffi_type_context_s',
                       ('types', rffi.VOIDPP),
                       ('globals', rffi.CArrayPtr(GLOBAL_S)),
                       ('fields', rffi.CArrayPtr(FIELD_S)),
                       ('struct_unions', rffi.CArrayPtr(STRUCT_UNION_S)),
                       ('enums', rffi.CArrayPtr(ENUM_S)),
                       ('typenames', rffi.CArrayPtr(TYPENAME_S)),
                       ('num_globals', rffi.INT),
                       ('num_struct_unions', rffi.INT),
                       ('num_enums', rffi.INT),
                       ('num_typenames', rffi.INT),
                       ('includes', rffi.CCHARPP))

PINFO = rffi.CStructPtr('struct _cffi_parse_info_s',
                        ('ctx', PCTX),
                        ('output', rffi.VOIDPP),
                        ('output_size', rffi.UINT),
                        ('error_location', rffi.SIZE_T),
                        ('error_message', rffi.CCHARP))

parse_c_type = llexternal('parse_c_type', [PINFO, rffi.CCHARP], rffi.INT)
