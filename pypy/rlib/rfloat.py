"""Float constants"""

import math
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib import objectmodel
from pypy.rpython.extfunc import register_external
from pypy.annotation.model import SomeString

USE_SHORT_FLOAT_REPR = True # XXX make it a translation option?

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(includes=["float.h"])

float_constants = ["DBL_MAX", "DBL_MIN", "DBL_EPSILON"]
int_constants = ["DBL_MAX_EXP", "DBL_MAX_10_EXP",
                 "DBL_MIN_EXP", "DBL_MIN_10_EXP",
                 "DBL_DIG", "DBL_MANT_DIG",
                 "FLT_RADIX", "FLT_ROUNDS"]
for const in float_constants:
    setattr(CConfig, const, rffi_platform.DefinedConstantDouble(const))
for const in int_constants:
    setattr(CConfig, const, rffi_platform.DefinedConstantInteger(const))
del float_constants, int_constants, const

globals().update(rffi_platform.configure(CConfig))

def rstring_to_float(s):
    return rstring_to_float_impl(s)

def rstring_to_float_impl(s):
    if USE_SHORT_FLOAT_REPR:
        from pypy.rlib.rdtoa import strtod
        return strtod(s)
    sign, before_point, after_point, exponent = break_up_float(s)
    if not before_point and not after_point:
        raise ValueError
    return parts_to_float(sign, before_point, after_point, exponent)

def oo_rstring_to_float(s):
    from pypy.rpython.annlowlevel import oostr
    from pypy.rpython.ootypesystem import ootype
    lls = oostr(s)
    return ootype.ooparse_float(lls)

register_external(rstring_to_float, [SomeString(can_be_None=False)], float,
                  llimpl=rstring_to_float_impl,
                  ooimpl=oo_rstring_to_float,
                  sandboxsafe=True)


# float as string  -> sign, beforept, afterpt, exponent
def break_up_float(s):
    i = 0

    sign = ''
    before_point = ''
    after_point = ''
    exponent = ''

    if s[i] in '+-':
        sign = s[i]
        i += 1

    while i < len(s) and s[i] in '0123456789':
        before_point += s[i]
        i += 1

    if i == len(s):
        return sign, before_point, after_point, exponent

    if s[i] == '.':
        i += 1
        while i < len(s) and s[i] in '0123456789':
            after_point += s[i]
            i += 1
            
        if i == len(s):
            return sign, before_point, after_point, exponent

    if s[i] not in  'eE':
        raise ValueError

    i += 1
    if i == len(s):
        raise ValueError

    if s[i] in '-+':
        exponent += s[i]
        i += 1

    if i == len(s):
        raise ValueError
    
    while i < len(s) and s[i] in '0123456789':
        exponent += s[i]
        i += 1

    if i != len(s):
        raise ValueError

    return sign, before_point, after_point, exponent

# string -> float helper

def parts_to_float(sign, beforept, afterpt, exponent):
    "NOT_RPYTHON"
    if not exponent:
        exponent = '0'
    return float("%s%s.%se%s" % (sign, beforept, afterpt, exponent))

# float -> string

DTSF_STR_PRECISION = 12

DTSF_SIGN      = 0x1
DTSF_ADD_DOT_0 = 0x2
DTSF_ALT       = 0x4

DIST_FINITE   = 1
DIST_NAN      = 2
DIST_INFINITY = 3

# Equivalent to CPython's PyOS_double_to_string
def _formatd(x, code, precision, flags):
    "NOT_RPYTHON"
    if flags & DTSF_ALT:
        alt = '#'
    else:
        alt = ''

    if code == 'r':
        fmt = "%r"
    else:
        fmt = "%%%s.%d%s" % (alt, precision, code)
    s = fmt % (x,)

    if flags & DTSF_ADD_DOT_0:
        # We want float numbers to be recognizable as such,
        # i.e., they should contain a decimal point or an exponent.
        # However, %g may print the number as an integer;
        # in such cases, we append ".0" to the string.
        for c in s:
            if c in '.eE':
                break
        else:
            s += '.0'
    elif code == 'r' and s.endswith('.0'):
        s = s[:-2]

    return s

def formatd(x, code, precision, flags=0):
    if USE_SHORT_FLOAT_REPR:
        from pypy.rlib.rdtoa import dtoa_formatd
        return dtoa_formatd(x, code, precision, flags)
    else:
        return _formatd(x, code, precision, flags)

def double_to_string(value, tp, precision, flags):
    if isnan(value):
        special = DIST_NAN
    elif isinf(value):
        special = DIST_INFINITY
    else:
        special = DIST_FINITE
    result = formatd(value, tp, precision, flags)
    return result, special

def round_double(value, ndigits):
    if USE_SHORT_FLOAT_REPR:
        return round_double_short_repr(value, ndigits)
    else:
        return round_double_fallback_repr(value, ndigits)

def round_double_short_repr(value, ndigits):
    # The basic idea is very simple: convert and round the double to
    # a decimal string using _Py_dg_dtoa, then convert that decimal
    # string back to a double with _Py_dg_strtod.  There's one minor
    # difficulty: Python 2.x expects round to do
    # round-half-away-from-zero, while _Py_dg_dtoa does
    # round-half-to-even.  So we need some way to detect and correct
    # the halfway cases.

    # a halfway value has the form k * 0.5 * 10**-ndigits for some
    # odd integer k.  Or in other words, a rational number x is
    # exactly halfway between two multiples of 10**-ndigits if its
    # 2-valuation is exactly -ndigits-1 and its 5-valuation is at
    # least -ndigits.  For ndigits >= 0 the latter condition is
    # automatically satisfied for a binary float x, since any such
    # float has nonnegative 5-valuation.  For 0 > ndigits >= -22, x
    # needs to be an integral multiple of 5**-ndigits; we can check
    # this using fmod.  For -22 > ndigits, there are no halfway
    # cases: 5**23 takes 54 bits to represent exactly, so any odd
    # multiple of 0.5 * 10**n for n >= 23 takes at least 54 bits of
    # precision to represent exactly.

    sign = copysign(1.0, value)
    value = abs(value)

    # find 2-valuation value
    m, expo = math.frexp(value)
    while m != math.floor(m):
        m *= 2.0
        expo -= 1

    # determine whether this is a halfway case.
    halfway_case = 0
    if expo == -ndigits - 1:
        if ndigits >= 0:
            halfway_case = 1
        elif ndigits >= -22:
            # 22 is the largest k such that 5**k is exactly
            # representable as a double
            five_pow = 1.0
            for i in range(-ndigits):
                five_pow *= 5.0
            if math.fmod(value, five_pow) == 0.0:
                halfway_case = 1

    # round to a decimal string; use an extra place for halfway case
    strvalue = formatd(value, 'f', ndigits + halfway_case)

    if halfway_case:
        buf = [c for c in strvalue]
        if ndigits >= 0:
            endpos = len(buf) - 1
        else:
            endpos = len(buf) + ndigits
        # Sanity checks: there should be exactly ndigits+1 places
        # following the decimal point, and the last digit in the
        # buffer should be a '5'
        if not objectmodel.we_are_translated():
            assert buf[endpos] == '5'
            if '.' in buf:
                assert endpos == len(buf) - 1
                assert buf.index('.') == len(buf) - ndigits - 2

        # increment and shift right at the same time
        i = endpos - 1
        carry = 1
        while i >= 0:
            digit = ord(buf[i])
            if digit == ord('.'):
                buf[i+1] = chr(digit)
                i -= 1
                digit = ord(buf[i])

            carry += digit - ord('0')
            buf[i+1] = chr(carry % 10 + ord('0'))
            carry /= 10
            i -= 1
        buf[0] = chr(carry + ord('0'))
        if ndigits < 0:
            buf.append('0')

        strvalue = ''.join(buf)

    return sign * rstring_to_float(strvalue)

# fallback version, to be used when correctly rounded
# binary<->decimal conversions aren't available
def round_double_fallback_repr(value, ndigits):
    if ndigits >= 0:
        if ndigits > 22:
            # pow1 and pow2 are each safe from overflow, but
            # pow1*pow2 ~= pow(10.0, ndigits) might overflow
            pow1 = math.pow(10.0, ndigits - 22)
            pow2 = 1e22
        else:
            pow1 = math.pow(10.0, ndigits)
            pow2 = 1.0

        y = (value * pow1) * pow2
        # if y overflows, then rounded value is exactly x
        if isinf(y):
            return value

    else:
        pow1 = math.pow(10.0, -ndigits);
        pow2 = 1.0 # unused; for translation
        y = value / pow1

    if y >= 0.0:
        z = math.floor(y + 0.5)
    else:
        z = math.ceil(y - 0.5)
    if math.fabs(y-z) == 1.0:   # obscure case, see the test
        z = y

    if ndigits >= 0:
        z = (z / pow2) / pow1
    else:
        z *= pow1
    return z

INFINITY = 1e200 * 1e200
NAN = INFINITY / INFINITY

try:
    # Try to get math functions added in 2.6.
    from math import isinf, isnan, copysign, acosh, asinh, atanh, log1p
except ImportError:
    def isinf(x):
        "NOT_RPYTHON"
        return x == INFINITY or x == -INFINITY

    def isnan(v):
        "NOT_RPYTHON"
        return v != v

    def copysign(x, y):
        """NOT_RPYTHON. Return x with the sign of y"""
        if x < 0.:
            x = -x
        if y > 0. or (y == 0. and math.atan2(y, -1.) > 0.):
            return x
        else:
            return -x

    _2_to_m28 = 3.7252902984619141E-09; # 2**-28
    _2_to_p28 = 268435456.0; # 2**28
    _ln2 = 6.93147180559945286227E-01

    def acosh(x):
        "NOT_RPYTHON"
        if isnan(x):
            return NAN
        if x < 1.:
            raise ValueError("math domain error")
        if x >= _2_to_p28:
            if isinf(x):
                return x
            else:
                return math.log(x) + _ln2
        if x == 1.:
            return 0.
        if x >= 2.:
            t = x * x
            return math.log(2. * x - 1. / (x + math.sqrt(t - 1.0)))
        t = x - 1.0
        return log1p(t + math.sqrt(2. * t + t * t))

    def asinh(x):
        "NOT_RPYTHON"
        absx = abs(x)
        if isnan(x) or isinf(x):
            return x
        if absx < _2_to_m28:
            return x
        if absx > _2_to_p28:
            w = math.log(absx) + _ln2
        elif absx > 2.:
            w = math.log(2. * absx + 1. / (math.sqrt(x * x + 1.) + absx))
        else:
            t = x * x
            w = log1p(absx + t / (1. + math.sqrt(1. + t)))
        return copysign(w, x)

    def atanh(x):
        "NOT_RPYTHON"
        if isnan(x):
            return x
        absx = abs(x)
        if absx >= 1.:
            raise ValueError("math domain error")
        if absx < _2_to_m28:
            return x
        if absx < .5:
            t = absx + absx
            t = .5 * log1p(t + t * absx / (1. - absx))
        else:
            t = .5 * log1p((absx + absx) / (1. - absx))
        return copysign(t, x)

    def log1p(x):
        "NOT_RPYTHON"
        from pypy.rlib import rfloat
        if abs(x) < rfloat.DBL_EPSILON // 2.:
            return x
        elif -.5 <= x <= 1.:
            y = 1. + x
            return math.log(y) - ((y - 1.) - x) / y
        else:
            return math.log(1. + x)

try:
    from math import expm1 # Added in Python 2.7.
except ImportError:
    def expm1(x):
        "NOT_RPYTHON"
        if abs(x) < .7:
            u = math.exp(x)
            if u == 1.:
                return x
            return (u - 1.) * x / math.log(u)
        return math.exp(x) - 1.

def round_away(x):
    # round() from libm, which is not available on all platforms!
    absx = abs(x)
    if absx - math.floor(absx) >= .5:
        r = math.ceil(absx)
    else:
        r = math.floor(absx)
    return copysign(r, x)

