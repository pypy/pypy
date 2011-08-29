from pypy.rlib.rarithmetic import intmask
from pypy.jit.metainterp import history
from pypy.rpython.lltypesystem import rffi
from pypy.jit.backend.llsupport.descr import (
    DynamicIntCallDescr, NonGcPtrCallDescr, FloatCallDescr, VoidCallDescr,
    LongLongCallDescr, getCallDescrClass)

class UnsupportedKind(Exception):
    pass

def get_call_descr_dynamic(cpu, ffi_args, ffi_result, extrainfo=None):
    """Get a call descr: the types of result and args are represented by
    rlib.libffi.types.*"""
    try:
        reskind = get_ffi_type_kind(cpu, ffi_result)
        argkinds = [get_ffi_type_kind(cpu, arg) for arg in ffi_args]
    except UnsupportedKind:
        return None
    arg_classes = ''.join(argkinds)
    if reskind == history.INT:
        size = intmask(ffi_result.c_size)
        signed = is_ffi_type_signed(ffi_result)
        return DynamicIntCallDescr(arg_classes, size, signed, extrainfo)
    elif reskind == history.REF:
        return  NonGcPtrCallDescr(arg_classes, extrainfo)
    elif reskind == history.FLOAT:
        return FloatCallDescr(arg_classes, extrainfo)
    elif reskind == history.VOID:
        return VoidCallDescr(arg_classes, extrainfo)
    elif reskind == 'L':
        return LongLongCallDescr(arg_classes, extrainfo)
    elif reskind == 'S':
        SingleFloatCallDescr = getCallDescrClass(rffi.FLOAT)
        return SingleFloatCallDescr(arg_classes, extrainfo)
    assert False

def get_ffi_type_kind(cpu, ffi_type):
    from pypy.rlib.libffi import types
    kind = types.getkind(ffi_type)
    if kind == 'i' or kind == 'u':
        return history.INT
    elif cpu.supports_floats and kind == 'f':
        return history.FLOAT
    elif kind == 'v':
        return history.VOID
    elif cpu.supports_longlong and (kind == 'I' or kind == 'U'):     # longlong
        return 'L'
    elif cpu.supports_singlefloats and kind == 's':    # singlefloat
        return 'S'
    raise UnsupportedKind("Unsupported kind '%s'" % kind)

def is_ffi_type_signed(ffi_type):
    from pypy.rlib.libffi import types
    kind = types.getkind(ffi_type)
    return kind != 'u'
