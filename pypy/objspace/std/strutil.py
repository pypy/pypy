"""
Pure Python implementation of string utilities.
"""

from pypy.rpython.rarithmetic import r_uint, ovfcheck

# XXX factor more functions out of stringobject.py.
# This module is independent from PyPy.

def strip_spaces(s):
    # XXX this is not locate-dependent
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
            raise ParseStringError, 'empty literal for %s()' % (self.fname,)        
        
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
            try:
                result =  ovfcheck(p.sign * result)
            except OverflowError:
                raise ParseStringOverflowError(p)
            else:
                return result
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
    w_base = space.newlong(r_uint(p.base))
    w_result = space.newlong(r_uint(0))
    while True:
        digit = p.next_digit()
        if digit == -1:
            if p.sign == -1:
                w_result = space.neg(w_result)
            # XXX grumble
            from pypy.objspace.std.longobject import W_LongObject
            assert isinstance(w_result, W_LongObject)
            return w_result
        w_result = space.add(space.mul(w_result,w_base),space.newlong(r_uint(digit)))

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
        raise ParseStringError("invalid string literal for float()")

    i += 1
    if i == len(s):
        raise ParseStringError("invalid string literal for float()")

    if s[i] in '-+':
        exponent += s[i]
        i += 1

    if i == len(s):
        raise ParseStringError("invalid string literal for float()")
    
    while i < len(s) and s[i] in '0123456789':
        exponent += s[i]
        i += 1

    if i != len(s):
        raise ParseStringError("invalid string literal for float()")

    return sign, before_point, after_point, exponent


def string_to_float(s):
    s = strip_spaces(s)

    if not s:
        raise ParseStringError("empty string for float()")

    sign, before_point, after_point, exponent = break_up_float(s)
    
    if not before_point and not after_point:
        raise ParseStringError("invalid string literal for float()")

    r = 0.0
    i = len(before_point) - 1
    j = 0
    while i >= 0:
        d = float(ord(before_point[i]) - ord('0'))
        r += d * (10.0 ** j)
        i -= 1
        j += 1

    i = 0
    while i < len(after_point):
        d = float(ord(after_point[i]) - ord('0'))
        r += d * (10.0 ** (-i-1))
        i += 1

    if exponent:
        # XXX this fails for float('0.' + '0'*100 + '1e400')
        # XXX later!
        try:
            e = string_to_int(exponent)
        except ParseStringOverflowError:
            if exponent[0] == '-':
                e = -400
            else:
                e = 400
        if e > 0:
            if e >= 400:
                r = 1e200 * 1e200
            else:
                while e > 0:
                    r *= 10.0
                    e -= 1
        else:
            if e <= -400:
                r = 0.0
            else:
                while e < 0:
                    r /= 10.0
                    e += 1

    if sign == '-':
        r = -r

    return r

# old version temporarily left here for comparison
old_string_to_float = string_to_float

# 57 bits are more than needed in any case.
# to allow for some rounding, we take one
# digit more.
MANTISSA_DIGITS = len(str( (1L << 57)-1 )) + 1

def string_to_float(s):
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
    # digits. Exponent computation is done in integer, unless
    # we get an overflow, where we fall back to float.
    # Usage of long numbers is explicitly avoided, because
    # we want to be able to work without longs as a PyPy option.

    # Observations:
    # because we are working on a 10-basis, which leads to
    # precision loss when multiplying by a power of 10, we need to be
    # careful about order of operation:
    # additions must be made starting with the lowest digits
    # powers of 10.0 should be calculated using **, because this is
    # more exact than multiplication.
    # avoid division/multiplication as much as possible.

    # The plan:
    # 1) parse the string into pieces.
    # 2) pre-calculate digit exponent dexp.
    # 3) truncate and adjust dexp.
    # 4) compute the exponent.
    #    add the number of digits before the point to the exponent.
    #    if we get an overflow here, we try to compute the exponent
    #    by intermediate floats.
    # 5) check the exponent for overflow and truncate to +-400.
    # 6) add/multiply the digits in, adjusting e.

    # XXX: limitations:
    # the algorithm is probably not optimum concerning the resulting
    # bit pattern, but very close to it. pre-computing to binary
    # numbers would give less rounding in the last digit. But this is
    # quite hard to do without longs.

    s = strip_spaces(s)

    if not s:
        raise ParseStringError("empty string for float()")

    # 1) parse the string into pieces.
    sign, before_point, after_point, exponent = break_up_float(s)
    
    if not before_point and not after_point:
        raise ParseStringError("invalid string literal for float()")

    # 2) pre-calculate digit exponent dexp.
    dexp = len(before_point)

    # 3) truncate and adjust dexp.
    digits = before_point + after_point
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

    # 4) compute the exponent.
    if not exponent:
        exponent = '0'
    try:
        e = string_to_int(exponent)
        e = ovfcheck(e + dexp)
    except (ParseStringOverflowError, OverflowError):
        fe = string_to_float(exponent) + dexp
        try:
            e = ovfcheck(int(fe))
        except OverflowError:
            # 4) check the exponent for overflow and truncate to +-400.
            if exponent[0] == '-':
                e = -400
            else:
                e = 400
    # 5) check the exponent for overflow and truncate to +-400.
    if e >= 400:
        e = 400
    elif e <= -400:
        e = -400
    # e is now in a range that does not overflow on additions.

    # 6) add/multiply the digits in, adjusting e.
    r = 0.0
    try:
        while p >= 0:
            # note: exponentiation is intentionally used for
            # exactness. If time is an issue, this can easily
            # be kept in a cache for every digit value.
            r += (ord(digits[p]) - ord('0')) * 10.0 ** e
            p -= 1
            e += 1
    except OverflowError:
        r =1e200 * 1e200

    if sign == '-':
        r = -r

    return r
