from pypy.rlib.rarithmetic import intmask
from pypy.jit.metainterp import history
from pypy.jit.backend.llsupport.descr import DynamicIntCallDescr, NonGcPtrCallDescr,\
    FloatCallDescr, VoidCallDescr

def get_call_descr_dynamic(ffi_args, ffi_result, extrainfo=None):
    """Get a call descr: the types of result and args are represented by
    rlib.libffi.types.*"""
    try:
        reskind = get_ffi_type_kind(ffi_result)
        argkinds = [get_ffi_type_kind(arg) for arg in ffi_args]
    except KeyError:
        return None # ??
    arg_classes = ''.join(argkinds)
    if reskind == history.INT:
        size = intmask(ffi_result.c_size)
        return DynamicIntCallDescr(arg_classes, size, extrainfo)
    elif reskind == history.REF:
        return  NonGcPtrCallDescr(arg_classes, extrainfo)
    elif reskind == history.FLOAT:
        return FloatCallDescr(arg_classes, extrainfo)
    elif reskind == history.VOID:
        return VoidCallDescr(arg_classes, extrainfo)
    assert False

def get_ffi_type_kind(ffi_type):
    from pypy.rlib.libffi import types
    kind = types.getkind(ffi_type)
    if kind == 'i':
        return history.INT
    elif kind == 'f':
        return history.FLOAT
    elif kind == 'v':
        return history.VOID
    assert False, "Unsuported kind '%s'" % kind
