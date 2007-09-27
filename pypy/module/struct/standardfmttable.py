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

def pack_pad(fmtiter, count):
    for i in range(count):
        fmtiter.result.append('\x00')

def pack_char(fmtiter):
    string = fmtiter.accept_str_arg()
    if len(string) != 1:
        raise StructError("expected a string of length 1")
    c = string[0]   # string->char conversion for the annotator
    fmtiter.result.append(c)

def pack_string(fmtiter, count):
    string = fmtiter.accept_str_arg()
    if len(string) < count:
        fmtiter.result += string
        for i in range(len(string), count):
            fmtiter.result.append('\x00')
    else:
        fmtiter.result += string[:count]

def pack_pascal(fmtiter, count):
    string = fmtiter.accept_str_arg()
    prefix = len(string)
    if prefix >= count:
        prefix = count - 1
        if prefix < 0:
            raise StructError("bad '0p' in struct format")
    if prefix > 255:
        prefixchar = '\xff'
    else:
        prefixchar = chr(prefix)
    fmtiter.result.append(prefixchar)
    fmtiter.result += string[:prefix]
    for i in range(1 + prefix, count):
        fmtiter.result.append('\x00')

def pack_float(fmtiter):
    xxx

# ____________________________________________________________

native_int_size = struct.calcsize("l")

def make_int_packer(size, signed, _memo={}):
    try:
        return _memo[size, signed]
    except KeyError:
        pass
    if signed:
        min = -(2 ** (8*size-1))
        max = (2 ** (8*size-1)) - 1
        if size <= native_int_size:
            accept_method = 'accept_int_arg'
        else:
            accept_method = 'accept_longlong_arg'
            min = r_longlong(min)
            max = r_longlong(max)
    else:
        min = 0
        max = (2 ** (8*size)) - 1
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
    unroll_revrange_size = unrolling_iterable(range(size-1, -1, -1))

    def pack_int(fmtiter):
        method = getattr(fmtiter, accept_method)
        value = method()
        if value < min or value > max:
            raise StructError(errormsg)
        if fmtiter.bigendian:
            for i in unroll_revrange_size:
                x = (value >> (8*i)) & 0xff
                fmtiter.result.append(chr(x))
        else:
            for i in unroll_revrange_size:
                fmtiter.result.append(chr(value & 0xff))
                value >>= 8

    _memo[size, signed] = pack_int
    return pack_int

# ____________________________________________________________

def unpack_pad(fmtiter, count):
    fmtiter.read(count)

def unpack_char(fmtiter):
    fmtiter.appendobj(fmtiter.read(1))

def unpack_string(fmtiter, count):
    fmtiter.appendobj(fmtiter.read(count))

def unpack_pascal(fmtiter, count):
    if count == 0:
        raise StructError("bad '0p' in struct format")
    data = fmtiter.read(count)
    end = 1 + ord(data[0])
    if end > count:
        end = count
    fmtiter.appendobj(data[1:end])

def unpack_float(fmtiter):
    xxx

# ____________________________________________________________

def make_int_unpacker(size, signed, _memo={}):
    try:
        return _memo[size, signed]
    except KeyError:
        pass
    if signed:
        max = (2 ** (8*size-1)) - 1
        if size <= native_int_size:
            inttype = int
        else:
            inttype = r_longlong
    else:
        max = None
        if size < native_int_size:
            inttype = int
        elif size == native_int_size:
            inttype = r_uint
        else:
            inttype = r_ulonglong
    unroll_range_size = unrolling_iterable(range(size))

    def unpack_int(fmtiter):
        intvalue = inttype(0)
        s = fmtiter.read(size)
        idx = 0
        if fmtiter.bigendian:
            for i in unroll_range_size:
                intvalue <<= 8
                intvalue |= ord(s[idx])
                idx += 1
        else:
            for i in unroll_range_size:
                intvalue |= inttype(ord(s[idx])) << (8*i)
                idx += 1
        if max is not None and intvalue > max:
            intvalue -= max
            intvalue -= max
            intvalue -= 2
        fmtiter.appendobj(intvalue)

    _memo[size, signed] = unpack_int
    return unpack_int

# ____________________________________________________________

standard_fmttable = {
    'x':{ 'size' : 1, 'pack' : pack_pad, 'unpack' : unpack_pad,
          'needcount' : True },
    'c':{ 'size' : 1, 'pack' : pack_char, 'unpack' : unpack_char},
    's':{ 'size' : 1, 'pack' : pack_string, 'unpack' : unpack_string,
          'needcount' : True },
    'p':{ 'size' : 1, 'pack' : pack_pascal, 'unpack' : unpack_pascal,
          'needcount' : True },
    'f':{ 'size' : 4, 'pack' : pack_float, 'unpack' : unpack_float},
    'd':{ 'size' : 8, 'pack' : pack_float, 'unpack' : unpack_float},
    }    

for c, size in [('b', 1), ('h', 2), ('i', 4), ('l', 4), ('q', 8)]:
    standard_fmttable[c] = {'size': size,
                            'pack': make_int_packer(size, True),
                            'unpack': make_int_unpacker(size, True)}
    standard_fmttable[c.upper()] = {'size': size,
                                    'pack': make_int_packer(size, False),
                                    'unpack': make_int_unpacker(size, False)}
