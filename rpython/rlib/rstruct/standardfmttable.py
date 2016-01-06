"""
The format table for standard sizes and alignments.
"""

# Note: we follow Python 2.5 in being strict about the ranges of accepted
# values when packing.

import struct

from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong
from rpython.rlib.rstruct import ieee
from rpython.rlib.rstruct.error import StructError, StructOverflowError
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.strstorage import str_storage_getitem
from rpython.rlib import rarithmetic
from rpython.rtyper.lltypesystem import rffi

native_is_bigendian = struct.pack("=i", 1) == struct.pack(">i", 1)
native_is_ieee754 = float.__getformat__('double').startswith('IEEE')

def pack_pad(fmtiter, count):
    fmtiter.result.append_multiple_char('\x00', count)

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
        fmtiter.result.append(string)
        fmtiter.result.append_multiple_char('\x00', count - len(string))
    else:
        fmtiter.result.append_slice(string, 0, count)

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
    fmtiter.result.append_slice(string, 0, prefix)
    fmtiter.result.append_multiple_char('\x00', count - (1 + prefix))

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

def make_int_packer(size, signed, _memo={}):
    key = size, signed
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
        if not min <= value <= max:
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

USE_FASTPATH = True    # set to False by some tests
ALLOW_SLOWPATH = True  # set to False by some tests

class CannotUnpack(Exception):
    pass

@specialize.memo()
def unpack_fastpath(TYPE):
    @specialize.argtype(0)
    def do_unpack_fastpath(fmtiter):
        size = rffi.sizeof(TYPE)
        strbuf, pos = fmtiter.get_buffer_as_string_maybe()
        if strbuf is None or pos % size != 0 or not USE_FASTPATH:
            raise CannotUnpack
        fmtiter.skip(size)
        return str_storage_getitem(TYPE, strbuf, pos)
    return do_unpack_fastpath

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

def make_ieee_unpacker(TYPE):
    @specialize.argtype(0)
    def unpack_ieee(fmtiter):
        size = rffi.sizeof(TYPE)
        if fmtiter.bigendian != native_is_bigendian or not native_is_ieee754:
            # fallback to the very slow unpacking code in ieee.py
            data = fmtiter.read(size)
            fmtiter.appendobj(ieee.unpack_float(data, fmtiter.bigendian))
            return
        ## XXX check if the following code is still needed
        ## if not str_storage_supported(TYPE):
        ##     # this happens e.g. on win32 and ARM32: we cannot read the string
        ##     # content as an array of doubles because it's not properly
        ##     # aligned. But we can read a longlong and convert to float
        ##     assert TYPE == rffi.DOUBLE
        ##     assert rffi.sizeof(TYPE) == 8
        ##     return unpack_longlong2float(fmtiter)
        try:
            # fast path
            val = unpack_fastpath(TYPE)(fmtiter)
        except CannotUnpack:
            # slow path, take the slice
            input = fmtiter.read(size)
            val = str_storage_getitem(TYPE, input, 0)
        fmtiter.appendobj(float(val))
    return unpack_ieee

@specialize.argtype(0)
def unpack_longlong2float(fmtiter):
    from rpython.rlib.rstruct.runpack import runpack
    from rpython.rlib.longlong2float import longlong2float
    s = fmtiter.read(8)
    llval = runpack('q', s) # this is a bit recursive, I know
    doubleval = longlong2float(llval)
    fmtiter.appendobj(doubleval)


unpack_double = make_ieee_unpacker(rffi.DOUBLE)
unpack_float = make_ieee_unpacker(rffi.FLOAT)

# ____________________________________________________________

def get_rffi_int_type(size, signed):
    for TYPE in rffi.platform.numbertype_to_rclass:
        if (rffi.sizeof(TYPE) == size and
            rarithmetic.is_signed_integer_type(TYPE) == signed):
            return TYPE
    raise KeyError("Cannot find an int type size=%d, signed=%d" % (size, signed))

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
    TYPE = get_rffi_int_type(size, signed)

    @specialize.argtype(0)
    def unpack_int_fastpath_maybe(fmtiter):
        if fmtiter.bigendian != native_is_bigendian or not native_is_ieee754: ## or not str_storage_supported(TYPE):
            return False
        try:
            intvalue = unpack_fastpath(TYPE)(fmtiter)
        except CannotUnpack:
            return False
        if not signed and size < native_int_size:
            intvalue = rarithmetic.intmask(intvalue)
        intvalue = inttype(intvalue)
        fmtiter.appendobj(intvalue)
        return True

    @specialize.argtype(0)
    def unpack_int(fmtiter):
        if unpack_int_fastpath_maybe(fmtiter):
            return
        # slow path
        if not ALLOW_SLOWPATH:
            # we enter here only on some tests
            raise ValueError("fastpath not taken :(")
        intvalue = inttype(0)
        s = fmtiter.read(size)
        idx = 0
        if fmtiter.bigendian:
            for i in unroll_range_size:
                x = ord(s[idx])
                if signed and i == 0 and x >= 128:
                    x -= 256
                intvalue <<= 8
                intvalue |= inttype(x)
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
                    'unpack' : unpack_float},
    'd':{ 'size' : 8, 'pack' : make_float_packer(8),
                    'unpack' : unpack_double},
    '?':{ 'size' : 1, 'pack' : pack_bool, 'unpack' : unpack_bool},
    }

for c, size in [('b', 1), ('h', 2), ('i', 4), ('l', 4), ('q', 8)]:
    standard_fmttable[c] = {'size': size,
                            'pack': make_int_packer(size, True),
                            'unpack': make_int_unpacker(size, True)}
    standard_fmttable[c.upper()] = {'size': size,
                                    'pack': make_int_packer(size, False),
                                    'unpack': make_int_unpacker(size, False)}
