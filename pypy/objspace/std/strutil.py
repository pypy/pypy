"""
Pure Python implementation of string utilities.
"""

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

class InvalidLiteral(Exception):
    pass

def _parse_string(s, literal, base, fname):
    # internal utility for string_to_int() and string_to_long().
    sign = 1
    if s.startswith('-'):
        sign = -1
        s = s[1:]
    elif s.startswith('+'):
        s = s[1:]
    if base == 0:
        if s.startswith('0x') or s.startswith('0X'):
            base = 16
        elif s.startswith('0'):
            base = 8
        else:
            base = 10
    elif base < 2 or base > 36:
        raise ValueError, "%s() base must be >= 2 and <= 36" % (fname,)
    try:
        if not s:
            raise InvalidLiteral
        if base == 16 and (s.startswith('0x') or s.startswith('0X')):
            s = s[2:]
        # XXX uses int-to-long overflow so far
        result = 0
        for c in s:
            digit = ord(c)
            if '0' <= c <= '9':
                digit -= ord('0')
            elif 'A' <= c <= 'Z':
                digit = (digit - ord('A')) + 10
            elif 'a' <= c <= 'z':
                digit = (digit - ord('a')) + 10
            else:
                raise InvalidLiteral
            if digit >= base:
                raise InvalidLiteral
            result = result*base + digit
        return result * sign
    except InvalidLiteral:
        if literal:
            raise ValueError, 'invalid literal for %s(): %s' % (fname, literal)
        else:
            raise ValueError, 'empty literal for %s()' % (fname,)

def string_to_int(s, base=10):
    """Utility to converts a string to an integer (or possibly a long).
    If base is 0, the proper base is guessed based on the leading
    characters of 's'.  Raises ValueError in case of error.
    """
    s = literal = strip_spaces(s)
    return _parse_string(s, literal, base, 'int')

def string_to_long(s, base=10):
    """As string_to_int(), but ignores an optional 'l' or 'L' suffix."""
    s = literal = strip_spaces(s)
    if (s.endswith('l') or s.endswith('L')) and base < 22:
        # in base 22 and above, 'L' is a valid digit!  try: long('L',22)
        s = s[:-1]
    return long(_parse_string(s, literal, base, 'long'))
