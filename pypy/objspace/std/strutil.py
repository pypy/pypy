"""
Pure Python implementation of string utilities.
"""

from pypy.rlib.rarithmetic import ovfcheck, break_up_float, parts_to_float,\
     INFINITY, NAN
from pypy.rlib.rbigint import rbigint, parse_digit_string
from pypy.interpreter.error import OperationError
import math

# XXX factor more functions out of stringobject.py.
# This module is independent from PyPy.

def strip_spaces(s):
    # XXX this is not locale-dependent
    p = 0
    q = len(s)
    while p < q and s[p] in ' \f\n\r\t\v':
        p += 1
    while p < q and s[q-1] in ' \f\n\r\t\v':
        q -= 1
    assert q >= p     # annotator hint, don't remove
    return s[p:q]

class ParseStringError(Exception):
    def __init__(self, msg):
        self.msg = msg

class ParseStringOverflowError(Exception):
    def __init__(self, parser):
        self.parser = parser

# iterator-like class
class NumberStringParser:

    def error(self):
        raise ParseStringError("invalid literal for %s() with base %d: '%s'" %
                               (self.fname, self.base, self.literal))

    def __init__(self, s, literal, base, fname):
        self.literal = literal
        self.fname = fname
        sign = 1
        if s.startswith('-'):
            sign = -1
            s = strip_spaces(s[1:])
        elif s.startswith('+'):
            s = strip_spaces(s[1:])
        self.sign = sign
        
        if base == 0:
            if s.startswith('0x') or s.startswith('0X'):
                base = 16
            elif s.startswith('0b') or s.startswith('0B'):
                base = 2
            elif s.startswith('0'): # also covers the '0o' case
                base = 8
            else:
                base = 10
        elif base < 2 or base > 36:
            raise ParseStringError, "%s() base must be >= 2 and <= 36" % (fname,)
        self.base = base

        if base == 16 and (s.startswith('0x') or s.startswith('0X')):
            s = s[2:]
        if base == 8 and (s.startswith('0o') or s.startswith('0O')):
            s = s[2:]
        if base == 2 and (s.startswith('0b') or s.startswith('0B')):
            s = s[2:]
        if not s:
            self.error()
        self.s = s
        self.n = len(s)
        self.i = 0

    def rewind(self):
        self.i = 0

    def next_digit(self): # -1 => exhausted
        if self.i < self.n:
            c = self.s[self.i]
            digit = ord(c)
            if '0' <= c <= '9':
                digit -= ord('0')
            elif 'A' <= c <= 'Z':
                digit = (digit - ord('A')) + 10
            elif 'a' <= c <= 'z':
                digit = (digit - ord('a')) + 10
            else:
                self.error()
            if digit >= self.base:
                self.error()
            self.i += 1
            return digit
        else:
            return -1

def string_to_int(s, base=10):
    """Utility to converts a string to an integer.
    If base is 0, the proper base is guessed based on the leading
    characters of 's'.  Raises ParseStringError in case of error.
    Raises ParseStringOverflowError in case the result does not fit.
    """
    s = literal = strip_spaces(s)
    p = NumberStringParser(s, literal, base, 'int')
    base = p.base
    result = 0
    while True:
        digit = p.next_digit()
        if digit == -1:
            return result

        if p.sign == -1:
            digit = -digit

        try:
            result = ovfcheck(result * base)
            result = ovfcheck(result + digit)
        except OverflowError:
            raise ParseStringOverflowError(p)

def string_to_bigint(s, base=10, parser=None):
    """As string_to_int(), but ignores an optional 'l' or 'L' suffix
    and returns an rbigint."""
    if parser is None:
        s = literal = strip_spaces(s)
        if (s.endswith('l') or s.endswith('L')) and base < 22:
            # in base 22 and above, 'L' is a valid digit!  try: long('L',22)
            s = s[:-1]
        p = NumberStringParser(s, literal, base, 'long')
    else:
        p = parser
    return parse_digit_string(p)

# Tim's comment:
# 57 bits are more than needed in any case.
# to allow for some rounding, we take one
# digit more.

# In the PyPy case, we can compute everything at compile time:
# XXX move this stuff to some central place, it is now also
# in _float_formatting.

def calc_mantissa_bits():
    bits = 1 # I know it is almost always 53, but let it compute...
    while 1:
        pattern = (1L << bits) - 1
        comp = long(float(pattern))
        if comp != pattern:
            return bits - 1
        bits += 1

MANTISSA_BITS = calc_mantissa_bits()
del calc_mantissa_bits
MANTISSA_DIGITS = len(str( (1L << MANTISSA_BITS)-1 )) + 1

def string_to_float(s):
    """
    Conversion of string to float.
    This version tries to only raise on invalid literals.
    Overflows should be converted to infinity whenever possible.

    Expects an unwrapped string and return an unwrapped float.
    """

    s = strip_spaces(s)

    if not s:
        raise ParseStringError("empty string for float()")


    low = s.lower()
    if low == "-inf" or low == "-infinity":
        return -INFINITY
    elif low == "inf" or low == "+inf":
        return INFINITY
    elif low == "infinity" or low == "+infinity":
        return INFINITY
    elif low == "nan" or low == "-nan" or low == "+nan":
        return NAN

    # 1) parse the string into pieces.
    try:
        sign, before_point, after_point, exponent = break_up_float(s)
    except ValueError:
        raise ParseStringError("invalid literal for float()")
    
    digits = before_point + after_point
    if not digits:
        raise ParseStringError("invalid literal for float()")

    # 2) pre-calculate digit exponent dexp.
    dexp = len(before_point)

    # 3) truncate and adjust dexp.
    p = 0
    plim = dexp + len(after_point)
    while p < plim and digits[p] == '0':
        p += 1
        dexp -= 1
    digits = digits[p : p + MANTISSA_DIGITS]
    p = len(digits) - 1
    while p >= 0 and digits[p] == '0':
        p -= 1
    dexp -= p + 1
    p += 1
    assert p >= 0
    digits = digits[:p]
    if len(digits) == 0:
        digits = '0'

    # 4) compute the exponent and truncate to +-400
    if not exponent:
        exponent = '0'
    long_exponent = rbigint.fromdecimalstr(exponent)
    long_exponent = long_exponent.add(rbigint.fromint(dexp))
    try:
        e = long_exponent.toint()
    except OverflowError:
        # XXX poking at internals
        e = long_exponent.sign * 400
    else:
        if e >= 400:
            e = 400
        elif e <= -400:
            e = -400

    # 5) compute the value using long math and proper rounding.
    b_digits = rbigint.fromdecimalstr(digits)
    b_10 = rbigint.fromint(10)
    b_1 = rbigint.fromint(1)
    if e >= 0:
        bits = 0
        b_power_of_ten = b_10.pow(rbigint.fromint(e))
        b_mantissa = b_digits.mul(b_power_of_ten)
    else:
        # compute a sufficiently large scale
        prec = MANTISSA_DIGITS * 2 + 22 # 128, maybe
        bits = - (int(math.ceil(-e / math.log10(2.0) - 1e-10)) + prec)
        b_scale = b_1.lshift(-bits)
        b_power_of_ten = b_10.pow(rbigint.fromint(-e))
        b_mantissa = b_digits.mul(b_scale).div(b_power_of_ten)

    # we now have a fairly large mantissa.
    # Shift it and round the last bit.

    # first estimate the bits and do a big shift
    mbits = b_mantissa._count_bits()
    needed = MANTISSA_BITS
    if mbits > needed:
        if mbits > needed+1:
            shifted = mbits - (needed+1)
            b_mantissa = b_mantissa.rshift(shifted)
            bits += shifted
        # do the rounding
        bits += 1
        round = b_mantissa.is_odd()
        b_mantissa = b_mantissa.rshift(1).add(rbigint.fromint(round))

    try:
        r = math.ldexp(b_mantissa.tofloat(), bits)
        # XXX I guess we do not check for overflow in ldexp as we agreed to!
        if r == 2*r and r != 0.0:
            raise OverflowError
    except OverflowError:
        r = INFINITY

    if sign == '-':
        r = -r

    return r
