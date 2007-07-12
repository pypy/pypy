#!/usr/bin/env python

import ctypes

import py

def primitive_pointer_repr(tp_s):
    return 'lltype.Ptr(lltype.FixedSizeArray(%s, 1))' % tp_s

# XXX any automatic stuff here?
SIMPLE_TYPE_MAPPING = {
    ctypes.c_int   : 'rffi.INT',
    ctypes.c_uint  : 'rffi.UINT',
    ctypes.c_voidp : 'rffi.VOIDP',
}

class RffiSource(object):
    def __init__(self, structures=None, code=None):
        # ctypes structure -> code mapping
        if structures is None:
            self.structures = {}
        else:
            self.structures = structures
        # rest of the code
        if code is None:
            self.code = py.code.Source()
        else:
            self.code = code

    def __add__(self, other):
        structs = self.structures.copy()
        structs.update(other.structures)
        code = py.code.Source(self.code, other.code)
        return RffiSource(structs, code)

    def __iadd__(self, other):
        self.structures.update(other.structures)
        self.code = py.code.Source(self.code, other.code)
        return self

    def proc_struct(self, tp):
        name = tp.__name__
        real_name = 'c_' + name
        real_name = real_name.rstrip('_structure')
        real_name += '_structure'
        if tp not in self.structures:
            fields = ["('%s', %s)" % (name_, self.proc_tp(field_tp))
                      for name_, field_tp in tp._fields_]
            fields_repr = ", ".join(fields)
            self.structures[tp] = py.code.Source(
                "%s = rffi.CStruct('%s', %s)"%(real_name, name,
                                              fields_repr))
        return real_name

    def proc_tp(self, tp):
        try:
            return SIMPLE_TYPE_MAPPING[tp]
        except KeyError:
            pass
        if issubclass(tp, ctypes._Pointer):
            if issubclass(tp._type_, ctypes._SimpleCData):
                return "lltype.Ptr(lltype.Array(%s, hints={'nolength': True}))"\
                       % self.proc_tp(tp._type_)
            return "lltype.Ptr(%s)" % self.proc_tp(tp._type_)
        elif issubclass(tp, ctypes.Structure):
            return self.proc_struct(tp)
        raise NotImplementedError("Not implemented mapping for %s" % tp)

    def proc_func(self, func):
        name = func.__name__
        src = py.code.Source("""
        c_%s = rffi.llexternal('%s', [%s], %s)
        """%(name, name, ", ".join([self.proc_tp(arg) for
                                   arg in func.argtypes]),
             self.proc_tp(func.restype)))
        self.code = py.code.Source(self.code, src)
