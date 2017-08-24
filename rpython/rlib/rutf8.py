""" This file is about supporting unicode strings in RPython,
represented by a byte string that is exactly the UTF-8 version
(for some definition of UTF-8).

This doesn't support Python 2's unicode characters beyond 0x10ffff,
which are theoretically possible to obtain using strange tricks like
the array or ctypes modules.

Fun comes from surrogates.  Various functions don't normally accept
any unicode character betwen 0xd800 and 0xdfff, but do if you give
the 'allow_surrogates = True' flag.
"""

from rpython.rlib.objectmodel import enforceargs
from rpython.rlib.rstring import StringBuilder
from rpython.rlib import jit
from rpython.rlib.rarithmetic import r_uint


def unichr_as_utf8(code, allow_surrogates=False):
    """Encode code (numeric value) as utf8 encoded string
    """
    code = r_uint(code)
    if code <= r_uint(0x7F):
        # Encode ASCII
        return chr(code)
    if code <= r_uint(0x07FF):
        return chr((0xc0 | (code >> 6))) + chr((0x80 | (code & 0x3f)))
    if code <= r_uint(0xFFFF):
        if not allow_surrogates and 0xD800 <= code <= 0xDfff:
            raise ValueError
        return (chr((0xe0 | (code >> 12))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f))))
    if code <= r_uint(0x10FFFF):
        return (chr((0xf0 | (code >> 18))) +
                chr((0x80 | ((code >> 12) & 0x3f))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f))))
    raise ValueError

def unichr_as_utf8_append(builder, code, allow_surrogates=False):
    """Encode code (numeric value) as utf8 encoded string
    and emit the result into the given StringBuilder.
    """
    code = r_uint(code)
    if code <= r_uint(0x7F):
        # Encode ASCII
        builder.append(chr(code))
        return
    if code <= r_uint(0x07FF):
        builder.append(chr((0xc0 | (code >> 6))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return
    if code <= r_uint(0xFFFF):
        if not allow_surrogates and 0xd800 <= code <= 0xdfff:
            raise ValueError
        builder.append(chr((0xe0 | (code >> 12))))
        builder.append(chr((0x80 | ((code >> 6) & 0x3f))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return
    if code <= r_uint(0x10FFFF):
        builder.append(chr((0xf0 | (code >> 18))))
        builder.append(chr((0x80 | ((code >> 12) & 0x3f))))
        builder.append(chr((0x80 | ((code >> 6) & 0x3f))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return
    raise ValueError

# note - table lookups are really slow. Measured on various elements of obama
#        chinese wikipedia, they're anywhere between 10% and 30% slower.
#        In extreme cases (small, only chinese text), they're 40% slower

def next_codepoint_pos(code, pos):
    """Gives the position of the next codepoint after pos.
    Assumes valid utf8.  'pos' must be before the end of the string.
    """
    chr1 = ord(code[pos])
    if chr1 <= 0x7F:
        return pos + 1
    if chr1 <= 0xDF:
        return pos + 2
    if chr1 <= 0xEF:
        return pos + 3
    return pos + 4

def prev_codepoint_pos(code, pos):
    """Gives the position of the previous codepoint.
    'pos' must not be zero.
    """
    pos -= 1
    chr1 = ord(code[pos])
    if chr1 <= 0x7F:
        return pos
    pos -= 1
    if ord(code[pos]) >= 0xC0:
        return pos
    pos -= 1
    if ord(code[pos]) >= 0xC0:
        return pos
    pos -= 1
    return pos

def compute_length_utf8(s):
    continuation_bytes = 0
    for i in range(len(s)):
        if 0x80 <= ord(s[i]) <= 0xBF:    # count the continuation bytes
            continuation_bytes += 1
    return len(s) - continuation_bytes

def codepoint_at_pos(code, pos):
    """ Give a codepoint in code at pos - assumes valid utf8, no checking!
    """
    ordch1 = ord(code[pos])
    if ordch1 <= 0x7F:
        return ordch1

    ordch2 = ord(code[pos+1])
    if ordch1 <= 0xDF:
        # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
        return (((ordch1 & 0x1F) << 6) +    # 0b00011111
                 (ordch2 & 0x3F))           # 0b00111111

    ordch3 = ord(code[pos+2])
    if ordch1 <= 0xEF:
        # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x0F) << 12) +     # 0b00001111
                ((ordch2 & 0x3F) << 6) +      # 0b00111111
                (ordch3 & 0x3F))              # 0b00111111

    ordch4 = ord(code[pos+3])
    if True:
        # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x07) << 18) +      # 0b00000111
                ((ordch2 & 0x3F) << 12) +      # 0b00111111
                ((ordch3 & 0x3F) << 6) +       # 0b00111111
                (ordch4 & 0x3F))               # 0b00111111
    assert False, "unreachable"

class CheckError(Exception):
    pass

@jit.elidable
def check_ascii(s):
    for i in range(len(s)):
        if ord(s[i]) > 0x7F:
            raise CheckError

#def utf8_encode_ascii(s, errors, encoding, msg, errorhandler):
#    res = StringBuilder(len(s))
#    u_pos = 0
#    pos = 0
#    while pos < len(s):
#        chr1 = s[pos]
#        if ord(chr1) < 0x80:
#            res.append(chr1)
#        else:
#            repl, _, _, _ = errorhandler(errors, encoding, msg, s, u_pos, u_pos + 1)
#            res.append(repl)
#        u_pos += 1
#        pos = next_codepoint_pos(s, pos)
#    return res.build()

#def str_decode_ascii(s, size, errors, errorhandler):
#    # ASCII is equivalent to the first 128 ordinals in Unicode.
#    result = StringBuilder(size)
#    pos = 0
#    while pos < size:
#        c = s[pos]
#        if ord(c) < 128:
#            result.append(c)
#        else:
#            r, _, _ = errorhandler(errors, "ascii", "ordinal not in range(128)",
#                                   s,  pos, pos + 1)
#            result.append(r)
#        pos += 1
#    return result.build(), pos, -1

def islinebreak(s, pos):
    chr1 = ord(s[pos])
    if 0xa <= chr1 <= 0xd:
        return True
    if 0x1c <= chr1 <= 0x1e:
        return True
    if chr1 == 0xc2:
        chr2 = ord(s[pos + 1])
        return chr2 == 0x85
    elif chr1 == 0xe2:
        chr2 = ord(s[pos + 1])
        if chr2 != 0x80:
            return False
        chr3 = ord(s[pos + 2])
        return chr3 == 0xa8 or chr3 == 0xa9
    return False

def isspace(s, pos):
    chr1 = ord(s[pos])
    if (chr1 == ord(' ') or chr1 == ord('\n') or chr1 == ord('\t') or
        chr1 == ord('\r')):
        return True # common
    if chr1 == 0x0b or chr1 == 0x0c or (chr1 >= 0x1c and chr1 <= 0x1f):
        return True # less common
    if chr1 < 0x80:
        return False
    # obscure cases
    chr2 = ord(s[pos + 1])
    if chr1 == 0xc2:
        return chr2 == 0x85 or chr2 == 0xa0
    if chr1 == 0xe2:
        if chr2 == 0x81 and s[pos + 2] == '\x9f':
            return True
        if chr2 != 0x80:
            return False
        chr3 = ord(s[pos + 2])
        if chr3 >= 0x80 and chr3 <= 0x8a:
            return True
        if chr3 == 0xa9 or chr3 == 0xa8 or chr3 == 0xaf:
            return True
        return False
    if chr1 == 0xe1:
        chr3 = ord(s[pos + 2])
        if chr2 == 0x9a and chr3 == 0x80:
            return True
        if chr2 == 0xa0 and chr3 == 0x8e:
            return True
        return False
    if chr1 == 0xe3 and chr2 == 0x80 and s[pos + 2] == '\x80':
        return True
    return False


def _invalid_cont_byte(ordch):
    return ordch>>6 != 0x2    # 0b10

_invalid_byte_2_of_2 = _invalid_cont_byte
_invalid_byte_3_of_3 = _invalid_cont_byte
_invalid_byte_3_of_4 = _invalid_cont_byte
_invalid_byte_4_of_4 = _invalid_cont_byte

@enforceargs(allow_surrogates=bool)
def _invalid_byte_2_of_3(ordch1, ordch2, allow_surrogates):
    return (ordch2>>6 != 0x2 or    # 0b10
            (ordch1 == 0xe0 and ordch2 < 0xa0)
            # surrogates shouldn't be valid UTF-8!
            or (ordch1 == 0xed and ordch2 > 0x9f and not allow_surrogates))

def _invalid_byte_2_of_4(ordch1, ordch2):
    return (ordch2>>6 != 0x2 or    # 0b10
            (ordch1 == 0xf0 and ordch2 < 0x90) or
            (ordch1 == 0xf4 and ordch2 > 0x8f))


@jit.elidable
def check_utf8(s, allow_surrogates=False):
    """Check that 's' is a utf-8-encoded byte string.
    Returns the length (number of chars) or raise CheckError.
    Note that surrogates are not handled specially here.
    """
    pos = 0
    continuation_bytes = 0
    while pos < len(s):
        ordch1 = ord(s[pos])
        pos += 1
        # fast path for ASCII
        if ordch1 <= 0x7F:
            continue

        if ordch1 <= 0xC1:
            raise CheckError

        if ordch1 <= 0xDF:
            continuation_bytes += 1
            if pos >= len(s):
                raise CheckError
            ordch2 = ord(s[pos])
            pos += 1

            if _invalid_byte_2_of_2(ordch2):
                raise CheckError
            # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
            continue

        if ordch1 <= 0xEF:
            continuation_bytes += 2
            if (pos + 2) > len(s):
                raise CheckError
            ordch2 = ord(s[pos])
            ordch3 = ord(s[pos + 1])
            pos += 2

            if _invalid_byte_2_of_3(ordch1, ordch2, allow_surrogates):
                raise CheckError
            elif _invalid_byte_3_of_3(ordch3):
                raise CheckError
            # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
            continue

        if ordch1 <= 0xF4:
            continuation_bytes += 3
            if (pos + 3) > len(s):
                raise CheckError
            ordch2 = ord(s[pos])
            ordch3 = ord(s[pos + 1])
            ordch4 = ord(s[pos + 2])
            pos += 3

            if _invalid_byte_2_of_4(ordch1, ordch2):
                raise CheckError
            elif _invalid_byte_3_of_4(ordch3):
                raise CheckError
            elif _invalid_byte_4_of_4(ordch4):
                raise CheckError
            # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
            continue

        raise CheckError

    assert pos == len(s)
    return pos - continuation_bytes
