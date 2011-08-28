"""
The format table for standard sizes and alignments.
"""

# Note: we follow Python 2.5 in being strict about the ranges of accepted
# values when packing.

import struct
from pypy.rlib.rstruct.error import StructError, StructOverflowError
from pypy.rlib.rstruct import ieee
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong
from pypy.rlib.objectmodel import specialize

# In the CPython struct module, pack() unconsistently accepts inputs
# that are out-of-range or floats instead of ints.  Should we emulate
# this?  Let's use a flag for now:

PACK_ACCEPTS_BROKEN_INPUT = True

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

def pack_bool(fmtiter):
    c = '\x01' if fmtiter.accept_bool_arg() else '\x00'
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

def make_float_packer(size):
    def packer(fmtiter):
        fl = fmtiter.accept_float_arg()
        try:
            return ieee.pack_float(fmtiter.result, fl, size, fmtiter.bigendian)
        except OverflowError:
            assert size == 4
            raise StructOverflowError("float too large for format 'f'")
    return packer

# ____________________________________________________________

native_int_size = struct.calcsize("l")

def min_max_acc_method(size, signed):
    if signed:
        min = -(2 ** (8*size-1))
        max = (2 ** (8*size-1)) - 1
        if size <= native_int_size:
            accept_method = 'accept_int_arg'
            min = int(min)
            max = int(max)
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
    return min, max, accept_method

def make_int_packer(size, signed, cpython_checks_range, _memo={}):
    if cpython_checks_range:
        check_range = True
    else:
        check_range = not PACK_ACCEPTS_BROKEN_INPUT
    key = (size, signed, check_range)
    try:
        return _memo[key]
    except KeyError:
        pass
    min, max, accept_method = min_max_acc_method(size, signed)
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
        if check_range:
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

    _memo[key] = pack_int
    return pack_int

# ____________________________________________________________

@specialize.argtype(0)
def unpack_pad(fmtiter, count):
    fmtiter.read(count)

@specialize.argtype(0)
def unpack_char(fmtiter):
    fmtiter.appendobj(fmtiter.read(1))

@specialize.argtype(0)
def unpack_bool(fmtiter):
    c = ord(fmtiter.read(1)[0])
    fmtiter.appendobj(bool(c))

@specialize.argtype(0)
def unpack_string(fmtiter, count):
    fmtiter.appendobj(fmtiter.read(count))

@specialize.argtype(0)
def unpack_pascal(fmtiter, count):
    if count == 0:
        raise StructError("bad '0p' in struct format")
    data = fmtiter.read(count)
    end = 1 + ord(data[0])
    if end > count:
        end = count
    fmtiter.appendobj(data[1:end])

def make_float_unpacker(size):
    @specialize.argtype(0)
    def unpacker(fmtiter):
        data = fmtiter.read(size)
        fmtiter.appendobj(ieee.unpack_float(data, fmtiter.bigendian))
    return unpacker

# ____________________________________________________________

def make_int_unpacker(size, signed, _memo={}):
    try:
        return _memo[size, signed]
    except KeyError:
        pass
    if signed:
        if size <= native_int_size:
            inttype = int
        else:
            inttype = r_longlong
    else:
        if size < native_int_size:
            inttype = int
        elif size == native_int_size:
            inttype = r_uint
        else:
            inttype = r_ulonglong
    unroll_range_size = unrolling_iterable(range(size))

    @specialize.argtype(0)
    def unpack_int(fmtiter):
        intvalue = inttype(0)
        s = fmtiter.input
        idx = fmtiter.get_pos_and_advance(size)
        if fmtiter.bigendian:
            for i in unroll_range_size:
                x = ord(s[idx])
                if signed and i == 0 and x >= 128:
                    x -= 256
                intvalue <<= 8
                intvalue |= x
                idx += 1
        else:
            for i in unroll_range_size:
                x = ord(s[idx])
                if signed and i == size - 1 and x >= 128:
                    x -= 256
                intvalue |= inttype(x) << (8*i)
                idx += 1
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
    'f':{ 'size' : 4, 'pack' : make_float_packer(4),
                    'unpack' : make_float_unpacker(4)},
    'd':{ 'size' : 8, 'pack' : make_float_packer(8),
                    'unpack' : make_float_unpacker(8)},
    '?':{ 'size' : 1, 'pack' : pack_bool, 'unpack' : unpack_bool},
    }

for c, size in [('b', 1), ('h', 2), ('i', 4), ('l', 4), ('q', 8)]:
    standard_fmttable[c] = {'size': size,
                            'pack': make_int_packer(size, True, True),
                            'unpack': make_int_unpacker(size, True)}
    standard_fmttable[c.upper()] = {'size': size,
                                    'pack': make_int_packer(size, False, True),
                                    'unpack': make_int_unpacker(size, False)}
