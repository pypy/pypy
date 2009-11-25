"""
Packing and unpacking of floats in the IEEE 32-bit and 64-bit formats.
"""

import math
from pypy.rlib.rarithmetic import r_longlong, isinf, isnan, INFINITY, NAN

def pack_float(result, number, size, bigendian):
    """Append to 'result' the 'size' characters of the 32-bit or 64-bit
    IEEE representation of the number.
    """
    if size == 4:
        bias = 127
        exp = 8
        prec = 23
    else:
        bias = 1023
        exp = 11
        prec = 52

    if isnan(number):
        sign = 0x80
        man, e = 1.5, bias + 1
    else:
        if number < 0:
            sign = 0x80
            number *= -1
        elif number == 0.0:
            for i in range(size):
                result.append('\x00')
            return
        else:
            sign = 0x00
        if isinf(number):
            man, e = 1.0, bias + 1
        else:
            man, e = math.frexp(number)

    if 0.5 <= man and man < 1.0:
        man *= 2
        e -= 1
    man -= 1
    e += bias
    power_of_two = r_longlong(1) << prec
    mantissa = r_longlong(power_of_two * man + 0.5)
    if mantissa >> prec :
        mantissa = 0
        e += 1

    for i in range(size-2):
        result.append(chr(mantissa & 0xff))
        mantissa >>= 8
    x = (mantissa & ((1<<(15-exp))-1)) | ((e & ((1<<(exp-7))-1))<<(15-exp))
    result.append(chr(x))
    x = sign | e >> (exp - 7)
    result.append(chr(x))
    if bigendian:
        first = len(result) - size
        last = len(result) - 1
        for i in range(size // 2):
            (result[first + i], result[last - i]) = (
                result[last - i], result[first + i])

def unpack_float(input, bigendian):
    """Interpret the 'input' string into a 32-bit or 64-bit
    IEEE representation a the number.
    """
    size = len(input)
    bytes = []
    if bigendian:
        reverse_mask = size - 1
    else:
        reverse_mask = 0
    nonzero = False
    for i in range(size):
        x = ord(input[i ^ reverse_mask])
        bytes.append(x)
        nonzero |= x
    if not nonzero:
        return 0.0
    if size == 4:
        bias = 127
        exp = 8
        prec = 23
    else:
        bias = 1023
        exp = 11
        prec = 52
    mantissa_scale_factor = 0.5 ** prec   # this is constant-folded if it's
                                          # right after the 'if'
    mantissa = r_longlong(bytes[size-2] & ((1<<(15-exp))-1))
    for i in range(size-3, -1, -1):
        mantissa = mantissa << 8 | bytes[i]
    mantissa = 1 + mantissa * mantissa_scale_factor
    mantissa *= 0.5
    e = (bytes[-1] & 0x7f) << (exp - 7)
    e += (bytes[size-2] >> (15 - exp)) & ((1<<(exp - 7)) -1)
    e -= bias
    e += 1
    sign = bytes[-1] & 0x80
    if e == bias + 2:
        if mantissa == 0.5:
            number = INFINITY
        else:
            return NAN
    else:
        number = math.ldexp(mantissa,e)
    if sign : number = -number
    return number
