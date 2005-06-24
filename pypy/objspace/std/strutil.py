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
                result =  ovfcheck(p.sign*result)
            except OverflowError:
                raise ParseStringOverflowError(p)
            else:
                return result
        try:
            result = ovfcheck(result*base)
            result = ovfcheck(result+digit)
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
                return space.neg(w_result)
            else:
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
        e = string_to_int(exponent)
        r *= 10.0 ** e

    if sign == '-':
        r = -r

    return r
