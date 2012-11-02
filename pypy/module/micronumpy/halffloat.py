# Based on numpy's halffloat.c, this is an implementation of routines
# for 16 bit float values.
from pypy.rpython.lltypesystem import rffi


def halfbits_to_floatbits(x):
    h_exp = x & 0x7c00
    f_sgn = (x & 0x8000) << 16
    if h_exp == 0: #0 or subnormal
        h_sig = x & 0x03ff
        if h_sig == 0:
            return f_sgn
        #Subnormal
        h_sig <<= 1;
        while (h_sig & 0x0400) == 0:
            h_sig <<= 1
            h_exp += 1
        f_exp = 127 - 15 - h_exp << 23
        f_sig = h_sig & 0x03ff << 13
        return f_sgn + f_exp + f_sig
    elif h_exp == 0x7c00: # inf or nan
        return f_sgn + 0x7f800000 + ((x & 0x03ff) << 13)
    # Just need to adjust the exponent and shift
    return f_sgn +((rffi.cast(rffi.UINT,(x & 0x7fff)) + 0x1c000) << 13)


def floatbits_to_halfbits(f):
    h_sgn = (f & 0x80000000) >> 16
    f_exp = f & 0x7f800000
    if f_exp >= 0x47800000:
        # Exponent overflow, convert to signed inf/nan
        if f_exp == 0x7f800000:
            # inf or nan
            f_sig = f & 0x007fffff
            if f_sig != 0:
                #nan - propagate the flag in the significand
                ret = 0x7c00 + (f_sig >> 13)
                # ... but make sure it stays a nan
                if ret == 0x7c00:
                    ret += 1
                return h_sgn + ret
            else:
                # signed inf
                return h_sgn + 0x7c00
        else:
            # overflow to signed inf
            # npy_set_floatstatus_overflow()
            return h_sgn + 0x7c00
    if f_exp <= 0x38000000:
        # Exponent underflow converts to a subnormal half or signed zero
        if f_exp < 0x33000000:
            # Signed zeros, subnormal floats, and floats with small
            # exponents all conver to signed zero halfs
            if f & 0x7fffffff != 0:
                pass
                # npy_set_floatstatus_underflow()
            return h_sgn
        # Make the subnormal significand
        f_exp >>= 23
        f_sig = 0x00800000 + (f & 0x007fffff)
        if (f_sig & ((1 << (126 - f_exp)) -1)) != 0:
            # not exactly represented, therefore underflowed
            pass
            # npy_set_floatstatus_underflow()
        f_sig >>= (113 - f_exp)
        # Handle rounding by adding 1 to the bit beyond half precision
        if (f_sig & 0x00003fff) != 0x00001000:
            # The last remaining bit is 1, and the rmaining bit pattern
            # is not 1000...0, so round up
            f_sig += 0x00001000
        h_sig = f_sig >> 13
        # If the rounding caused a bit to spill into h_exp, it will
        # increment h_exp from zero to one and h_sig will remain zero
        # which is the correct result.
        return h_sgn + h_sig
    # No overflow or underflow
    h_exp = (f_exp - 0x38000000)>> 13
    f_sig = f & 0x007fffff
    if (f_sig & 0x00003fff) != 0x00001000:
        # The last remaining bit is 1, and the rmaining bit pattern
        # is not 1000...0, so round up
        f_sig += 0x00001000
    h_sig = f_sig >> 13
    # If the rounding cuased a bit to spill into h_exp, it will
    # increment h_exp from zero to one and h_sig will remain zero
    # which is the correct result. However, h_exp may increment to
    # 15, at greatest, in which case the result overflows
    h_sig += h_exp
    if h_sig == 0x7c00:
        pass
        #npy_set_floatstatus_overflow()
    return h_sgn + h_sig    

def halfbits_to_doublebits(h):
    h_exp = h & 0x7c00
    d_sgn = h >>15 << 63
    if h_exp == 0: #0 or subnormal
        h_sig = h & 0x03ff
        if h_sig == 0:
            return d_sgn
        #Subnormal
        h_sig <<= 1;
        while (h_sig & 0x0400) == 0:
            h_sig <<= 1
            h_exp += 1
        d_exp = ((1023 - 15 - h_exp)) << 52
        d_sig = ((h_sig & 0x03ff)) << 42
        return d_sgn + d_exp + d_sig;
    elif h_exp == 0x7c00: # inf or nan
        return d_sgn + 0x7ff0000000000000 + ((h & 0x03ff) << 42)
    return d_sgn + (((h & 0x7fff) + 0xfc000) << 42)
    
def doublebits_to_halfbits(d):
    h_sgn = (d & 0x8000000000000000) >> 48
    d_exp = (d & 0x7ff0000000000000)
    if d_exp >= 0x40f0000000000000:
        # Exponent overflow, convert to signed inf/nan
        if d_exp == 0x7ff0000000000000:
            # inf or nan
            d_sig = d & 0x000fffffffffffff
            if d_sig != 0:
                #nan - propagate the flag in the significand
                ret = 0x7c00 + (d_sig >> 42)
                # ... but make sure it stays a nan
                if ret == 0x7c00:
                    ret += 1
                return h_sgn + ret
            else:
                # signed inf
                return h_sgn + 0x7c00
        else:
            # overflow to signed inf
            # npy_set_floatstatus_overflow()
            return h_sgn + 0x7c00
    if d_exp <= 0x3f00000000000000:
        # Exponent underflow converts to a subnormal half or signed zero
        if d_exp < 0x3e60000000000000:
            # Signed zeros, subnormal floats, and floats with small
            # exponents all conver to signed zero halfs
            if d & 0x7fffffffffffffff != 0:
                pass
                # npy_set_floatstatus_underflow()
            return h_sgn
        # Make the subnormal significand
        d_exp >>= 52
        d_sig = 0x0010000000000000 + (d & 0x000fffffffffffff)
        if (d_sig & ((1 << (1051 - d_exp)) - 1)) != 0:
            # not exactly represented, therefore underflowed
            pass
            # npy_set_floatstatus_underflow()
        d_sig >>= (1009 - d_exp)
        # Handle rounding by adding 1 to the bit beyond half precision
        if (d_sig & 0x000007ffffffffff) != 0x0000020000000000:
            # The last remaining bit is 1, and the rmaining bit pattern
            # is not 1000...0, so round up
            d_sig += 0x0000020000000000
        h_sig =  d_sig >> 42
        # If the rounding caused a bit to spill into h_exp, it will
        # increment h_exp from zero to one and h_sig will remain zero
        # which is the correct result.
        return h_sgn + h_sig
    # No overflow or underflow
    h_exp = (d_exp - 0x3f00000000000000) >> 42
    d_sig = d & 0x000fffffffffffff
    if (d_sig & 0x000007ffffffffff) != 0x0000020000000000:
        # The last remaining bit is 1, and the rmaining bit pattern
        # is not 1000...0, so round up
        d_sig += 0x0000020000000000
    h_sig =  d_sig >> 42
    # If the rounding cuased a bit to spill into h_exp, it will
    # increment h_exp from zero to one and h_sig will remain zero
    # which is the correct result. However, h_exp may increment to
    # 15, at greatest, in which case the result overflows
    h_sig += h_exp
    if h_sig == 0x7c00:
        pass
        #npy_set_floatstatus_overflow()
    return h_sgn + h_sig    
