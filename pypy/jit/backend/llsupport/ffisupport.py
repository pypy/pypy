from pypy.rlib.rarithmetic import intmask
from pypy.rpython.lltypesystem import rffi
from pypy.jit.backend.llsupport.descr import CallDescr

class UnsupportedKind(Exception):
    pass

def get_call_descr_dynamic(cpu, cif_description, extrainfo):
    """Get a call descr from the given CIF_DESCRIPTION"""
    ffi_result = cif_description.rtype
    try:
        reskind = get_ffi_type_kind(cpu, ffi_result)
        argkinds = [get_ffi_type_kind(cpu, atype)
                    for atype in cif_description.atypes]
    except UnsupportedKind:
        return None
    if reskind == 'v':
        result_size = 0
    else:
        result_size = intmask(ffi_result.c_size)
    argkinds = ''.join(argkinds)
    return CallDescr(argkinds, reskind, is_ffi_type_signed(ffi_result),
                     result_size, extrainfo, ffi_flags=cif_description.abi)

def get_ffi_type_kind(cpu, ffi_type):
    from pypy.rlib.jit_libffi import types
    kind = types.getkind(ffi_type)
    if ((not cpu.supports_floats and kind == 'f') or
        (not cpu.supports_longlong and kind == 'L') or
        (not cpu.supports_singlefloats and kind == 'S') or
        kind == '*'):
        raise UnsupportedKind("Unsupported kind '%s'" % kind)
    if kind == 'u':
        kind = 'i'
    return kind

def is_ffi_type_signed(ffi_type):
    from pypy.rlib.jit_libffi import types
    kind = types.getkind(ffi_type)
    return kind != 'u'
