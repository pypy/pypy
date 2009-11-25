"""
Pure Python implementation of string utilities.
"""

from pypy.rlib.rarithmetic import ovfcheck, break_up_float, parts_to_float
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
        if self.literal:
            raise ParseStringError, 'invalid literal for %s(): %s' % (self.fname, self.literal)
        else:
            raise ParseStringError, 'empty string for %s()' % (self.fname,)        
        
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
            elif s.startswith('0'):
                base = 8
            else:
                base = 10
        elif base < 2 or base > 36:
            raise ParseStringError, "%s() base must be >= 2 and <= 36" % (fname,)
        self.base = base

        if not s:
            self.error()
        if base == 16 and (s.startswith('0x') or s.startswith('0X')):
            s = s[2:]
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
    """Utility to converts a string to an integer (or possibly a long).
    If base is 0, the proper base is guessed based on the leading
    characters of 's'.  Raises ParseStringError in case of error.
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

def string_to_long(space, s, base=10, parser=None):
    return string_to_w_long(space, s, base, parser).longval()

def string_to_w_long(space, s, base=10, parser=None):
    """As string_to_int(), but ignores an optional 'l' or 'L' suffix."""
    if parser is None:
        s = literal = strip_spaces(s)
        if (s.endswith('l') or s.endswith('L')) and base < 22:
            # in base 22 and above, 'L' is a valid digit!  try: long('L',22)
            s = s[:-1]
        p = NumberStringParser(s, literal, base, 'long')
    else:
        p = parser
    w_base = space.newlong(p.base)
    w_result = space.newlong(0)
    while True:
        digit = p.next_digit()
        if digit == -1:
            if p.sign == -1:
                w_result = space.neg(w_result)
            # XXX grumble
            from pypy.objspace.std.longobject import W_LongObject
            assert isinstance(w_result, W_LongObject)
            return w_result
        w_result = space.add(space.mul(w_result,w_base), space.newlong(digit))

def string_to_float(s):
    """
    Conversion of string to float.
    This version tries to only raise on invalid literals.
    Overflows should be converted to infinity whenever possible.
    """

    s = strip_spaces(s)

    if not s:
        raise ParseStringError("empty string for float()")

    # 1) parse the string into pieces.
    try:
        sign, before_point, after_point, exponent = break_up_float(s)
    except ValueError:
        raise ParseStringError("invalid literal for float()")
    
    if not before_point and not after_point:
        raise ParseStringError("invalid literal for float()")

    try:
        return parts_to_float(sign, before_point, after_point, exponent)
    except ValueError:
        raise ParseStringError("invalid literal for float()")


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

# we keep this version for reference.
def applevel_string_to_float(s):
    """
    Conversion of string to float.
    This version tries to only raise on invalid literals.
    Overflows should be converted to infinity whenever possible.
    """
    # this version was triggered by Python 2.4 which adds
    # a test that breaks on overflow.
    # XXX The test still breaks for a different reason:
    # float must implement rich comparisons, where comparison
    # between infinity and a too large long does not overflow!

    # The problem:
    # there can be extreme notations of floats which are not
    # infinity.
    # For instance, this works in CPython:
    # float('1' + '0'*1000 + 'e-1000')
    # should evaluate to 1.0.
    # note: float('1' + '0'*10000 + 'e-10000')
    # does not work in CPython, but PyPy can do it, now.

    # The idea:
    # in order to compensate between very long digit strings
    # and extreme exponent numbers, we try to avoid overflows
    # by adjusting the exponent by the number of mantissa
    # digits. For simplicity, all computations are done in
    # long math.

    # The plan:
    # 1) parse the string into pieces.
    # 2) pre-calculate digit exponent dexp.
    # 3) truncate and adjust dexp.
    # 4) compute the exponent and truncate to +-400.
    # 5) compute the value using long math and proper rounding.

    # Positive results:
    # The algorithm appears appears to produce correct round-trip
    # values for the perfect input of _float_formatting.
    # Note:
    # XXX: the builtin rounding of long->float does not work, correctly.
    # Ask Tim Peters for the reasons why no correct rounding is done.
    # XXX: limitations:
    # - It is possibly not too efficient.
    # - Really optimum results need a more sophisticated algorithm
    #   like Bellerophon from William D. Clinger, cf.
    #   http://citeseer.csail.mit.edu/clinger90how.html
    
    s = strip_spaces(s)

    if not s:
        raise ParseStringError("empty string for float()")

    # 1) parse the string into pieces.
    try:
        sign, before_point, after_point, exponent = break_up_float(s)
    except ValueError:
        raise ParseStringError("invalid literal for float()")
        
    digits = before_point + after_point
    if digits:
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
    digits = digits[:p+1]
    if len(digits) == 0:
        digits = '0'

    # 4) compute the exponent and truncate to +-400
    if not exponent:
        exponent = '0'
    e = long(exponent) + dexp
    if e >= 400:
        e = 400
    elif e <= -400:
        e = -400

    # 5) compute the value using long math and proper rounding.
    lr = long(digits)
    if e >= 0:
        bits = 0
        m = lr * 10L ** e
    else:
        # compute a sufficiently large scale
        prec = MANTISSA_DIGITS * 2 + 22 # 128, maybe
        bits = - (int(math.ceil(-e / math.log10(2.0) - 1e-10)) + prec)
        scale = 2L ** -bits
        pten = 10L ** -e
        m = (lr * scale) // pten

    # we now have a fairly large mantissa.
    # Shift it and round the last bit.

    # first estimate the bits and do a big shift
    if m:
        mbits = int(math.ceil(math.log(m, 2) - 1e-10))
        needed = MANTISSA_BITS
        if mbits > needed:
            if mbits > needed+1:
                shifted = mbits - (needed+1)
                m >>= shifted
                bits += shifted
            # do the rounding
            bits += 1
            m = (m >> 1) + (m & 1)

    try:
        r = math.ldexp(m, bits)
    except OverflowError:
        r = 1e200 * 1e200 # produce inf, hopefully

    if sign == '-':
        r = -r

    return r


# the "real" implementation.
# for comments, see above.
# XXX probably this very specific thing should go into longobject?

def interp_string_to_float(space, s):
    """
    Conversion of string to float.
    This version tries to only raise on invalid literals.
    Overflows should be converted to infinity whenever possible.

    Expects an unwrapped string and return an unwrapped float.
    """

    s = strip_spaces(s)

    if not s:
        raise OperationError(space.w_ValueError, space.wrap(
            "empty string for float()"))

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

    # a few abbreviations
    from pypy.objspace.std import longobject
    mklong = longobject.W_LongObject.fromint
    d2long = longobject.W_LongObject.fromdecimalstr
    adlong = longobject.add__Long_Long
    longup = longobject.pow__Long_Long_None
    multip = longobject.mul__Long_Long
    divide = longobject.div__Long_Long
    lshift = longobject.lshift__Long_Long
    rshift = longobject.rshift__Long_Long

    # 4) compute the exponent and truncate to +-400
    if not exponent:
        exponent = '0'
    w_le = d2long(exponent)
    w_le = adlong(space, w_le, mklong(space, dexp))
    try:
        e = w_le.toint()
    except OverflowError:
        # XXX poking at internals
        e = w_le.num.sign * 400
    if e >= 400:
        e = 400
    elif e <= -400:
        e = -400

    # 5) compute the value using long math and proper rounding.
    w_lr = d2long(digits)
    w_10 = mklong(space, 10)
    w_1 = mklong(space, 1)
    if e >= 0:
        bits = 0
        w_pten = longup(space, w_10, mklong(space, e), space.w_None)
        w_m = multip(space, w_lr, w_pten)
    else:
        # compute a sufficiently large scale
        prec = MANTISSA_DIGITS * 2 + 22 # 128, maybe
        bits = - (int(math.ceil(-e / math.log10(2.0) - 1e-10)) + prec)
        w_scale = lshift(space, w_1, mklong(space, -bits))
        w_pten = longup(space, w_10, mklong(space, -e), None)
        w_tmp = multip(space, w_lr, w_scale)
        w_m = divide(space, w_tmp, w_pten)

    # we now have a fairly large mantissa.
    # Shift it and round the last bit.

    # first estimate the bits and do a big shift
    mbits = w_m._count_bits()
    needed = MANTISSA_BITS
    if mbits > needed:
        if mbits > needed+1:
            shifted = mbits - (needed+1)
            w_m = rshift(space, w_m, mklong(space, shifted))
            bits += shifted
        # do the rounding
        bits += 1
        round = w_m.is_odd()
        w_m = rshift(space, w_m, w_1)
        w_m = adlong(space, w_m, mklong(space, round))

    try:
        r = math.ldexp(w_m.tofloat(), bits)
        # XXX I guess we do not check for overflow in ldexp as we agreed to!
        if r == 2*r and r != 0.0:
            raise OverflowError
    except OverflowError:
        r = 1e200 * 1e200 # produce inf, hopefully

    if sign == '-':
        r = -r

    return r
