"""
Packing and unpacking of floats in the IEEE 32-bit and 64-bit formats.
"""

import math

from pypy.rlib import rarithmetic, rfloat, objectmodel, jit
from pypy.rlib.rarithmetic import r_ulonglong, r_ulonglonglong


def round_to_nearest(x):
    """Python 3 style round:  round a float x to the nearest int, but
    unlike the builtin Python 2.x round function:

      - return an int, not a float
      - do round-half-to-even, not round-half-away-from-zero.

    We assume that x is finite and nonnegative; expect wrong results
    if you use this for negative x.

    """
    int_part = r_ulonglong(x)
    frac_part = x - int_part
    if frac_part > 0.5 or frac_part == 0.5 and int_part & 1:
        int_part += 1
    return int_part


def float_unpack(Q, size):
    """Convert a 16-bit, 32-bit 64-bit integer created
    by float_pack into a Python float."""
    if size == 16 or size == 12:
        #Implement a x86-hardware extended 80 bit format
        MIN_EXP = -16381  # = sys.float_info.min_exp
        MAX_EXP = 16384   # = sys.float_info.max_exp
        MANT_DIG = 64    # = sys.float_info.mant_dig
        BITS = 80
        one = r_ulonglonglong(1)
    elif size == 8:
        MIN_EXP = -1021  # = sys.float_info.min_exp
        MAX_EXP = 1024   # = sys.float_info.max_exp
        MANT_DIG = 53    # = sys.float_info.mant_dig
        BITS = 64
        one = r_ulonglong(1)
    elif size == 4:
        MIN_EXP = -125   # C's FLT_MIN_EXP
        MAX_EXP = 128    # FLT_MAX_EXP
        MANT_DIG = 24    # FLT_MANT_DIG
        BITS = 32
        one = r_ulonglong(1)
    elif size == 2:
        MIN_EXP = -13   
        MAX_EXP = 16    
        MANT_DIG = 11
        BITS = 16
        one = r_ulonglong(1)
    else:
        raise ValueError("invalid size value")

    if not objectmodel.we_are_translated():
        # This tests generates wrong code when translated:
        # with gcc, shifting a 64bit int by 64 bits does
        # not change the value.
        if Q >> BITS:
            raise ValueError("input out of range")

    # extract pieces
    sign = rarithmetic.intmask(Q >> BITS - 1)
    exp = rarithmetic.intmask((Q & ((one << BITS - 1) - (one << MANT_DIG - 1))) >> MANT_DIG - 1)
    mant = Q & ((one << MANT_DIG - 1) - 1)

    if exp == MAX_EXP - MIN_EXP + 2:
        # nan or infinity
        result = rfloat.NAN if mant else rfloat.INFINITY
    elif exp == 0:
        # subnormal or zero
        result = math.ldexp(mant, MIN_EXP - MANT_DIG)
    else:
        # normal
        mant += one << MANT_DIG - 1
        result = math.ldexp(mant, exp + MIN_EXP - MANT_DIG - 1)
    return -result if sign else result


def float_pack(x, size):
    """Convert a Python float x into a 64-bit unsigned integer
    with the same byte representation."""
    return float_pack_helper(x, size, r_ulonglong)

def float_pack128(x, size):
    """Convert a Python float x into a 64-bit unsigned integer
    with the same byte representation."""
    return float_pack_helper(x, size, r_ulonglonglong)

def float_pack_helper(x, size, r_type):
    if size == 8:
        MIN_EXP = -1021  # = sys.float_info.min_exp
        MAX_EXP = 1024   # = sys.float_info.max_exp
        MANT_DIG = 53    # = sys.float_info.mant_dig
        BITS = 64
    elif size == 4:
        MIN_EXP = -125   # C's FLT_MIN_EXP
        MAX_EXP = 128    # FLT_MAX_EXP
        MANT_DIG = 24    # FLT_MANT_DIG
        BITS = 32
    elif size == 2:
        MIN_EXP = -13   
        MAX_EXP = 16    
        MANT_DIG = 11
        BITS = 16
    elif size == 16 or size == 12:
        #Implement a x86-hardware extended 80 bit format
        MIN_EXP = -16381  # = sys.float_info.min_exp
        MAX_EXP = 16384   # = sys.float_info.max_exp
        MANT_DIG = 64    # = sys.float_info.mant_dig
        BITS = 80
    else:
        raise ValueError("invalid size value")

    sign = rfloat.copysign(1.0, x) < 0.0
    if not rfloat.isfinite(x):
        if rfloat.isinf(x):
            mant = r_type(0)
            exp = MAX_EXP - MIN_EXP + 2
        else:  # rfloat.isnan(x):
            mant = r_type(1) << (MANT_DIG-2) # other values possible
            exp = MAX_EXP - MIN_EXP + 2
    elif x == 0.0:
        mant = r_type(0)
        exp = 0
    else:
        m, e = math.frexp(abs(x))  # abs(x) == m * 2**e
        exp = e - (MIN_EXP - 1)
        if exp > 0:
            # Normal case.
            mant = round_to_nearest(m * (r_type(1) << MANT_DIG))
            mant -= r_type(1) << MANT_DIG - 1
        else:
            # Subnormal case.
            if exp + MANT_DIG - 1 >= 0:
                mant = round_to_nearest(m * (r_type(1) << exp + MANT_DIG - 1))
            else:
                mant = r_type(0)
            exp = 0

        # Special case: rounding produced a MANT_DIG-bit mantissa.
        if not objectmodel.we_are_translated():
            assert 0 <= mant <= 1 << MANT_DIG - 1
        if mant == r_type(1) << MANT_DIG - 1:
            mant = r_type(0)
            exp += 1

        # Raise on overflow (in some circumstances, may want to return
        # infinity instead).
        if exp >= MAX_EXP - MIN_EXP + 2:
             raise OverflowError("float too large to pack in this format")

    # check constraints
    if not objectmodel.we_are_translated():
        assert 0 <= mant < 1 << MANT_DIG - 1
        assert 0 <= exp <= MAX_EXP - MIN_EXP + 2
        assert 0 <= sign <= 1

    exp = r_type(exp)
    sign = r_type(sign)
    return ((sign << BITS - 1) | (exp << MANT_DIG - 1)) | mant


@jit.unroll_safe
def pack_float(result, x, size, be):
    l = []
    unsigned = float_pack(x, size)
    for i in range(size):
        l.append(chr((unsigned >> (i * 8)) & 0xFF))
    if be:
        l.reverse()
    result.append("".join(l))


def unpack_float(s, be):
    unsigned = r_ulonglong(0)
    for i in range(len(s)):
        c = ord(s[len(s) - 1 - i if be else i])
        unsigned |= r_ulonglong(c) << (i * 8)
    return float_unpack(unsigned, len(s))
