#!/usr/bin/env python

import ctypes

import py

def primitive_pointer_repr(tp_s):
    return 'lltype.Ptr(lltype.FixedSizeArray(%s, 1))' % tp_s

# XXX any automatic stuff here?
SIMPLE_TYPE_MAPPING = {
    ctypes.c_int : 'rffi.INT',
    ctypes.c_voidp : primitive_pointer_repr('lltype.Void')
}

def proc_tp(tp):
    try:
        return SIMPLE_TYPE_MAPPING[tp]
    except KeyError:
        raise NotImplementedError("Not implemented mapping for %s" % tp)

def proc_func(func):
    name = func.__name__
    src = py.code.Source("""
    c_%s = rffi.llexternal('%s', [%s], %s)
    """%(name, name, ",".join([proc_tp(arg) for arg in func.argtypes]),
         proc_tp(func.restype)))
    return src
