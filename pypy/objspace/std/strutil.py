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

def string_to_int(s, base=10):
    """Utility to converts a string to an integer (or possibly a long).
    If base is 0, the proper base is guessed based on the leading
    characters of 's'.  Raises ValueError in case of error.
    """
    s = literal = strip_spaces(s)
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
        raise ValueError, "int() base must be >= 2 and <= 36"
    if not s:
        if not literal:
            raise ValueError, 'empty literal for int()'
        else:
            raise ValueError, 'invalid literal for int(): ' + literal
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
            raise ValueError, 'invalid literal for int(): ' + literal
        if digit >= base:
            raise ValueError, 'invalid literal for int(): ' + literal
        result = result*base + digit
    return result * sign
