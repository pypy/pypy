"""
The format table for standard sizes and alignments.
"""

# Note: we follow Python 2.5 in being strict about the ranges of accepted
# values when packing.

import struct
from pypy.module.struct.error import StructError
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong

# ____________________________________________________________

def pack_pad(fmtiter):
    fmtiter.result.append('\x00')

def pack_char(fmtiter):
    xxx

def pack_string(fmtiter):
    xxx

def pack_pascal(fmtiter):
    xxx

def pack_float(fmtiter):
    xxx

# ____________________________________________________________

native_int_size = struct.calcsize("l")

def make_int_packer(size, signed):
    if signed:
        min = -(2 ** (size-1))
        max = (2 ** (size-1)) - 1
        if size <= native_int_size:
            accept_method = 'accept_int_arg'
        else:
            accept_method = 'accept_longlong_arg'
            min = r_longlong(min)
            max = r_longlong(max)
    else:
        min = 0
        max = (2 ** size) - 1
        if size < native_int_size:
            accept_method = 'accept_int_arg'
        elif size == native_int_size:
            accept_method = 'accept_uint_arg'
            min = r_uint(min)
            max = r_uint(max)
        else:
            accept_method = 'accept_ulonglong_arg'
            min = r_ulonglong(min)
            max = r_ulonglong(max)
    if size > 1:
        plural = "s"
    else:
        plural = ""
    errormsg = "argument out of range for %d-byte%s integer format" % (size,
                                                                       plural)
    unroll_range_size = unrolling_iterable(range(size))

    def pack_int(fmtiter):
        method = getattr(fmtiter, accept_method)
        value = method()
        if value < min or value > max:
            raise StructError(errormsg)
        if fmtiter.bigendian:
            for i in unroll_range_size:
                x = (value >> (8*i)) & 0xff
                fmtiter.result.append(chr(x))
        else:
            for i in unroll_range_size:
                fmtiter.result.append(chr(value & 0xff))
                value >>= 8

    return pack_int

# ____________________________________________________________

def unpack_pad(fmtiter):
    xxx

def unpack_char(fmtiter):
    xxx

def unpack_string(fmtiter):
    xxx

def unpack_pascal(fmtiter):
    xxx

def unpack_float(fmtiter):
    xxx

# ____________________________________________________________

def make_int_unpacker(size, signed):
    return lambda fmtiter: xxx

# ____________________________________________________________

standard_fmttable = {
    'x':{ 'size' : 1, 'alignment' : 0, 'pack' : pack_pad, 'unpack' : unpack_pad},
    'c':{ 'size' : 1, 'alignment' : 0, 'pack' : pack_char, 'unpack' : unpack_char},
    's':{ 'size' : 1, 'alignment' : 0, 'pack' : pack_string, 'unpack' : unpack_string},
    'p':{ 'size' : 1, 'alignment' : 0, 'pack' : pack_pascal, 'unpack' : unpack_pascal},
    'f':{ 'size' : 4, 'alignment' : 0, 'pack' : pack_float, 'unpack' : unpack_float},
    'd':{ 'size' : 8, 'alignment' : 0, 'pack' : pack_float, 'unpack' : unpack_float},
    }    

for c, size in [('b', 1), ('h', 2), ('i', 4), ('q', 8)]:    # 'l' see below
    standard_fmttable[c] = {'size': size,
                            'alignment': 0,
                            'pack': make_int_packer(size, True),
                            'unpack': make_int_unpacker(size, True)}
    standard_fmttable[c.upper()] = {'size': size,
                                    'alignment': 0,
                                    'pack': make_int_packer(size, False),
                                    'unpack': make_int_unpacker(size, False)}

standard_fmttable['l'] = standard_fmttable['i']
standard_fmttable['L'] = standard_fmttable['I']
