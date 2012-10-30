# Based on numpy's halffloat.c, this is an implementation of routines
# for 16 bit float values.

#from pypy.rpython.lltypesystem import rffi
#from rffi import USHORT as uint16
#def tofloat(x):
#    return rffi.cast(rffi.FLOAT, x)

'''
def half_to_float(x):
    assert isinstance(x, float16)
    xbits = x.view(uint16)
    fbits = halffloatbits_to_floatbits(xbits)
    return uint32(fbits).view(float32) 

def float_to_half(f):
    assert isinstance(f, (float32, float))
    fbits = float32(f).view(uint32)
    xbits = floatbits_to_halfbits(fbits)
    return uint16(xbits).view(float16)
'''
def halfbits_to_floatbits(x):
    h_exp = x & 0x7c00
    f_sign = (x & 0x8000) << 16
    if h_exp == 0: #0 or subnormal
        h_sig = x & 0x03ff
        if h_sig == 0:
            return f_sign
        #Subnormal
        h_sig <<= 1;
        while (h_sig & 0x0400) == 0:
            h_sig <<= 1
            h_exp += 1
        f_exp = 127 - 15 - h_exp << 23
        f_sig = h_sig & 0x03ff << 13
        return f_sign & f_exp & f_sig
    elif h_exp == 0x7c00: # inf or nan
        return f_sign + 0x7f800000 + ((x & 0x03ff) << 13)
    # Just need to adjust the exponent and shift
    return f_sign + (((x & 0x7fff) + 0x1c000) << 13)


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
        # If the rounding cuased a bit to spill into h_exp, it will
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

