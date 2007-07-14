#!/usr/bin/env python

import ctypes

import py

def primitive_pointer_repr(tp_s):
    return 'lltype.Ptr(lltype.FixedSizeArray(%s, 1))' % tp_s

# XXX any automatic stuff here?
SIMPLE_TYPE_MAPPING = {
    ctypes.c_ubyte     : 'rffi.UCHAR',
    ctypes.c_byte      : 'rffi.CHAR',
    ctypes.c_char      : 'rffi.CHAR',
    ctypes.c_int8      : 'rffi.CHAR',
    ctypes.c_ushort    : 'rffi.USHORT',
    ctypes.c_short     : 'rffi.SHORT',
    ctypes.c_uint16    : 'rffi.USHORT',
    ctypes.c_int16     : 'rffi.SHORT',
    ctypes.c_int       : 'rffi.INT',
    ctypes.c_uint      : 'rffi.UINT',
    ctypes.c_int32     : 'rffi.INT',
    ctypes.c_uint32    : 'rffi.UINT',
    #ctypes.c_long      : 'rffi.LONG', # same as c_int..
    #ctypes.c_ulong     : 'rffi.ULONG',
    ctypes.c_longlong  : 'rffi.LONGLONG',
    ctypes.c_ulonglong : 'rffi.ULONGLONG',
    ctypes.c_int64     : 'rffi.LONGLONG',
    ctypes.c_uint64    : 'rffi.ULONGLONG',
    ctypes.c_voidp     : 'rffi.VOIDP',
    None               : 'rffi.lltype.Void', # XXX make a type in rffi
    ctypes.c_char_p    : 'rffi.CCHARP',
    ctypes.c_double    : 'rffi.lltype.Float', # XXX make a type in rffi
}

class RffiSource(object):
    def __init__(self, structs=None, source=None, includes=[], libraries=[],
            include_dirs=[]):
        # set of ctypes structs
        if structs is None:
            self.structs = set()
        else:
            self.structs = structs
        if source is None:
            self.source = py.code.Source()
        else:
            self.source = source
        includes = includes and "includes=%s, " % repr(tuple(includes)) or ''
        libraries = libraries and "libraries=%s, " % repr(tuple(libraries)) or ''
        include_dirs = include_dirs and \
            "include_dirs=%s, " % repr(tuple(include_dirs)) or ''
        self.extra_args = includes+libraries+include_dirs

    def __str__(self):
        return str(self.source)

    def __add__(self, other):
        structs = self.structs.copy()
        structs.update(other.structs)
        source = py.code.Source(self.source, other.source)
        return RffiSource(structs, source)

    def __iadd__(self, other):
        self.structs.update(other.structs)
        self.source = py.code.Source(self.source, other.source)
        return self

    def proc_struct(self, tp):
        name = tp.__name__
        if tp not in self.structs:
            fields = ["('%s', %s), " % (name_, self.proc_tp(field_tp))
                      for name_, field_tp in tp._fields_]
            fields_repr = ''.join(fields)
            self.structs.add(tp)
            src = py.code.Source(
                "%s = lltype.Struct('%s', %s hints={'external':'C'})"%(
                    name, name, fields_repr))
            self.source = py.code.Source(self.source, src)
        return name

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
        print "proc_func", func
        name = func.__name__
        src = py.code.Source("""
        %s = rffi.llexternal('%s', [%s], %s, %s)
        """%(name, name, ", ".join([self.proc_tp(arg) for arg in func.argtypes]),
             self.proc_tp(func.restype), self.extra_args))
        self.source = py.code.Source(self.source, src)

    def proc_namespace(self, ns):
        exempt = set(id(value) for value in ctypes.__dict__.values())
        for key, value in ns.items():
            if id(value) in exempt: 
                continue
            if isinstance(value, ctypes._CFuncPtr):
                print "func", key, value
                try:    
                    self.proc_func(value)
                except NotImplementedError:
                    print "skipped:", value
            #print value, value.__class__.__name__





