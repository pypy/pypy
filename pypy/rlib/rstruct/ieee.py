"""
Packing and unpacking of floats in the IEEE 32-bit and 64-bit formats.
"""

import math
from pypy.rlib.rarithmetic import r_longlong, r_ulonglong, isinf, isnan, INFINITY, NAN


def py3round(x):
    """Python 3 round function semantics, in Python 2 code.

    We want to round x to the nearest int, but:
      - return an int, not a float
      - do round-half-to-even, not round-half-away-from-zero.

    We assume that x is finite and nonnegative.

    """
    int_part = r_ulonglong(x)
    frac_part = x - int_part
    if frac_part > 0.5 or frac_part == 0.5 and (int_part & 1):
        int_part += 1
    return int_part


def float_pack(x, size):
    """Convert a Python float x into a 64-bit unsigned integer
    with the same byte representation."""

    if size == 8:
        MIN_EXP = -1021  # = sys.float_info.min_exp
        MAX_EXP = 1024   # = sys.float_info.max_exp
        MANT_DIG = 53    # = sys.float_info.mant_dig
    elif size == 4:
        MIN_EXP = -125   # C's FLT_MIN_EXP
        MAX_EXP = 128    # FLT_MAX_EXP
        MANT_DIG = 24    # FLT_MANT_DIG
    else:
        raise ValueError("invalid size value")

    sign = math.copysign(1.0, x) < 0.0
    if isinf(x):
        mant = 0
        exp = MAX_EXP - MIN_EXP + 2
    elif isnan(x):
        mant = 1 << (MANT_DIG-2)
        exp = MAX_EXP - MIN_EXP + 2
    elif x == 0.0:
        mant = 0
        exp = 0
    else:
        m, e = math.frexp(abs(x))
        if e < MIN_EXP:
            # Subnormal result (or possibly smallest normal, after rounding).
            if e < MIN_EXP - MANT_DIG:
                # Underflow to zero; not possible when size == 8.
                mant = r_ulonglong(0)
            else:
                # For size == 8, can substitute 'int' for 'py3round', both
                # here and below: the argument will always be integral.
                mant = py3round(m * (1 << e - (MIN_EXP - MANT_DIG)))
            exp = 0
        elif e > MAX_EXP:
            # Overflow to infinity: not possible when size == 8.
            raise OverflowError("float too large to pack with f format")
        else:
            mant = py3round(m * (1 << MANT_DIG))
            exp = e - MIN_EXP
    # N.B. It's important that the + mant really is an addition, not just a
    # bitwise 'or'.  In extreme cases, mant may have MANT_DIG+1 significant
    # bits, as a result of rounding.
    return ((sign << 8*size - 1) | (exp << MANT_DIG - 1)) + mant


def float_unpack(Q, size):
    """Convert a 32-bit or 64-bit integer created
    by float_pack into a Python float."""

    if size == 8:
        MIN_EXP = -1021  # = sys.float_info.min_exp
        MAX_EXP = 1024   # = sys.float_info.max_exp
        MANT_DIG = 53    # = sys.float_info.mant_dig
    elif size == 4:
        MIN_EXP = -125   # C's FLT_MIN_EXP
        MAX_EXP = 128    # FLT_MAX_EXP
        MANT_DIG = 24    # FLT_MANT_DIG
    else:
        raise ValueError("invalid size value")

    # extract pieces
    sign = Q >> 8*size - 1
    Q -= sign << 8*size - 1
    exp = Q >> MANT_DIG - 1
    Q -= exp << MANT_DIG - 1
    mant = Q

    if exp == MAX_EXP - MIN_EXP + 2:
        # nan or infinity
        result = float('nan') if mant else float('inf')
    elif exp == 0:
        # subnormal or zero
        result = math.ldexp(float(mant), MIN_EXP - MANT_DIG)
    else:
        # normal
        exp -= 1
        mant += 1 << MANT_DIG - 1
        result = math.ldexp(float(mant), exp + MIN_EXP - MANT_DIG)
    return -result if sign else result


def pack_float8(result, x):
    unsigned = float_pack(x, 8)
    for i in range(8):
        result.append(chr((unsigned >> (i * 8)) & 0xFF))


def unpack_float8(s):
    unsigned = r_ulonglong(0)
    for i in range(8):
        unsigned |= ord(s[7 - i]) << (i * 8)
    print unsigned
    return float_unpack(unsigned, 8)


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
