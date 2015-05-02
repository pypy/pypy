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


PCTX = rffi.CStructPtr('struct _cffi_type_context_s')
PINFO = rffi.CStructPtr('struct _cffi_parse_info_s',
                        ('ctx', PCTX),
                        ('output', rffi.VOIDPP),
                        ('output_size', rffi.UINT),
                        ('error_location', rffi.SIZE_T),
                        ('error_message', rffi.CCHARP))

parse_c_type = llexternal('parse_c_type', [PINFO, rffi.CCHARP], rffi.INT)
