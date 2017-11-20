import sys

from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import specialize
from rpython.rlib import rutf8
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib.rstring import StringBuilder
from pypy.module._codecs import interp_codecs

@specialize.memo()
def decode_error_handler(space):
    # Fast version of the "strict" errors handler.
    def raise_unicode_exception_decode(errors, encoding, msg, s,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeDecodeError,
                             space.newtuple([space.newtext(encoding),
                                             space.newbytes(s),
                                             space.newint(startingpos),
                                             space.newint(endingpos),
                                             space.newtext(msg)]))
    return raise_unicode_exception_decode

@specialize.memo()
def encode_error_handler(space):
    # Fast version of the "strict" errors handler.
    def raise_unicode_exception_encode(errors, encoding, msg, u, u_len,
                                       startingpos, endingpos):
        # XXX fix once we stop using runicode.py
        flag = _get_flag(u.decode('utf8'))
        raise OperationError(space.w_UnicodeEncodeError,
                             space.newtuple([space.newtext(encoding),
                                             space.newutf8(u, u_len, flag),
                                             space.newint(startingpos),
                                             space.newint(endingpos),
                                             space.newtext(msg)]))
    return raise_unicode_exception_encode

def convert_arg_to_w_unicode(space, w_arg, strict=None):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    assert not hasattr(space, 'is_fake_objspace')
    return W_UnicodeObject.convert_arg_to_w_unicode(space, w_arg, strict)

# ____________________________________________________________

def encode(space, w_data, encoding=None, errors='strict'):
    from pypy.objspace.std.unicodeobject import encode_object
    return encode_object(space, w_data, encoding, errors)

def combine_flags(one, two):
    if one == rutf8.FLAG_ASCII and two == rutf8.FLAG_ASCII:
        return rutf8.FLAG_ASCII
    elif (one == rutf8.FLAG_HAS_SURROGATES or
          two == rutf8.FLAG_HAS_SURROGATES):
        return rutf8.FLAG_HAS_SURROGATES
    return rutf8.FLAG_REGULAR


def _has_surrogate(u):
    for c in u:
        if 0xD800 <= ord(c) <= 0xDFFF:
            return True
    return False

def _get_flag(u):
    flag = rutf8.FLAG_ASCII
    for c in u:
        if 0xD800 <= ord(c) <= 0xDFFF:
            return rutf8.FLAG_HAS_SURROGATES
        if ord(c) >= 0x80:
            flag = rutf8.FLAG_REGULAR
    return flag

# These functions take and return unwrapped rpython strings
def decode_unicode_escape(space, string):
    state = space.fromcache(interp_codecs.CodecState)
    unicodedata_handler = state.get_unicodedata_handler(space)
    result_utf8, consumed, length, flag = str_decode_unicode_escape(
        string, "strict",
        final=True,
        errorhandler=decode_error_handler(space),
        ud_handler=unicodedata_handler)
    return result_utf8, length, flag

def decode_raw_unicode_escape(space, string):
    result_utf8, consumed, lgt, flag = str_decode_raw_unicode_escape(
        string, "strict",
        final=True, errorhandler=decode_error_handler(space))
    return result_utf8, lgt, flag

def check_ascii_or_raise(space, string):
    try:
        rutf8.check_ascii(string)
    except rutf8.CheckError as e:
        decode_error_handler(space)('strict', 'ascii',
                                    'ordinal not in range(128)', string,
                                    e.pos, e.pos + 1)
        assert False, "unreachable"

def check_utf8_or_raise(space, string, start=0, end=-1):
    # Surrogates are accepted and not treated specially at all.
    # If there happen to be two 3-bytes encoding a pair of surrogates,
    # you still get two surrogate unicode characters in the result.
    # These are the Python2 rules; Python3 differs.
    try:
        length, flag = rutf8.check_utf8(string, True, start, end)
    except rutf8.CheckError as e:
        # convert position into unicode position
        lgt, flags = rutf8.check_utf8(string, True, start, stop=e.pos)
        decode_error_handler(space)('strict', 'utf8', 'invalid utf-8', string,
                                    start + lgt, start + lgt + 1)
        assert False, "unreachable"
    return length, flag

def str_decode_ascii(s, errors, final, errorhandler):
    try:
        rutf8.check_ascii(s)
        return s, len(s), len(s), rutf8.FLAG_ASCII
    except rutf8.CheckError:
        return _str_decode_ascii_slowpath(s, errors, final, errorhandler)

def _str_decode_ascii_slowpath(s, errors, final, errorhandler):
    i = 0
    res = StringBuilder()
    while i < len(s):
        ch = s[i]
        if ord(ch) > 0x7F:
            r, i = errorhandler(errors, 'ascii', 'ordinal not in range(128)',
                s, i, i + 1)
            res.append(r)
        else:
            res.append(ch)
            i += 1
    ress = res.build()
    lgt, flag = rutf8.check_utf8(ress, True)
    return ress, len(s), lgt, flag

def str_decode_latin_1(s, errors, final, errorhandler):
    xxx

def utf8_encode_latin_1(s, errors, errorhandler):
    try:
        rutf8.check_ascii(s)
        return s
    except rutf8.CheckError:
        return _utf8_encode_latin_1_slowpath(s, errors, errorhandler)

def _utf8_encode_latin_1_slowpath(s, errors, errorhandler):
    res = StringBuilder(len(s))
    size = len(s)
    cur = 0
    i = 0
    while i < size:
        if ord(s[i]) <= 0x7F:
            res.append(s[i])
        else:
            oc = rutf8.codepoint_at_pos(s, i)
            if oc <= 0xFF:
                res.append(chr(oc))
                i += 1
            else:
                r, pos = errorhandler(errors, 'latin1',
                                      'ordinal not in range(256)', s, cur,
                                      cur + 1)
                res.append(r)
                for j in range(pos - cur):
                    i = rutf8.next_codepoint_pos(s, i)
                cur = pos
        cur += 1
        i += 1
    r = res.build()
    return r

def utf8_encode_ascii(utf8, errors, errorhandler):
    """ Don't be confused - this is a slowpath for errors e.g. "ignore"
    or an obscure errorhandler
    """
    res = StringBuilder()
    i = 0
    pos = 0
    while i < len(utf8):
        ch = rutf8.codepoint_at_pos(utf8, i)
        if ch >= 0x7F:
            msg = "ordinal not in range(128)"
            r, newpos = errorhandler(errors, 'ascii', msg, utf8,
                pos, pos + 1)
            for _ in range(newpos - pos):
                i = rutf8.next_codepoint_pos(utf8, i)
            pos = newpos
            res.append(r)
        else:
            res.append(chr(ch))
            i = rutf8.next_codepoint_pos(utf8, i)
            pos += 1

    s = res.build()
    return s

def str_decode_utf8(s, errors, final, errorhandler):
    """ Same as checking for the valid utf8, but we know the utf8 is not
    valid so we're trying to either raise or pack stuff with error handler.
    The key difference is that this is call_may_force
    """
    slen = len(s)
    res = StringBuilder(slen)
    pos = 0
    continuation_bytes = 0
    end = len(s)
    while pos < end:
        ordch1 = ord(s[pos])
        # fast path for ASCII
        if ordch1 <= 0x7F:
            pos += 1
            res.append(chr(ordch1))
            continue

        if ordch1 <= 0xC1:
            r, pos = errorhandler(errors, "utf8", "invalid start byte",
                    s, pos, pos + 1)
            res.append(r)
            continue

        pos += 1

        if ordch1 <= 0xDF:
            if pos >= end:
                if not final:
                    break
                r, pos = errorhandler(errors, "utf8", "unexpected end of data",
                    s, pos - 1, pos)
                res.append(r)
                continue
            ordch2 = ord(s[pos])

            if rutf8._invalid_byte_2_of_2(ordch2):
                r, pos = errorhandler(errors, "utf8", "invalid continuation byte",
                    s, pos - 1, pos)
                res.append(r)
                continue
            # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
            pos += 1
            continuation_bytes += 1
            res.append(chr(ordch1))
            res.append(chr(ordch2))
            continue

        if ordch1 <= 0xEF:
            if (pos + 2) > end:
                if not final:
                    break
                r, pos = errorhandler(errors, "utf8", "unexpected end of data",
                    s, pos - 1, pos + 1)
                res.append(r)
                continue
            ordch2 = ord(s[pos])
            ordch3 = ord(s[pos + 1])

            if rutf8._invalid_byte_2_of_3(ordch1, ordch2, True):
                r, pos = errorhandler(errors, "utf8", "invalid continuation byte",
                    s, pos - 1, pos)
                res.append(r)
                continue
            elif rutf8._invalid_byte_3_of_3(ordch3):
                r, pos = errorhandler(errors, "utf8", "invalid continuation byte",
                    s, pos - 1, pos + 1)
                res.append(r)
                continue
            pos += 2

            # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
            continuation_bytes += 2
            res.append(chr(ordch1))
            res.append(chr(ordch2))
            res.append(chr(ordch3))
            continue

        if ordch1 <= 0xF4:
            if (pos + 3) > end:
                if not final:
                    break
                r, pos = errorhandler(errors, "utf8", "unexpected end of data",
                    s, pos - 1, pos)
                res.append(r)
                continue
            ordch2 = ord(s[pos])
            ordch3 = ord(s[pos + 1])
            ordch4 = ord(s[pos + 2])

            if rutf8._invalid_byte_2_of_4(ordch1, ordch2):
                r, pos = errorhandler(errors, "utf8", "invalid continuation byte",
                    s, pos - 1, pos)
                res.append(r)
                continue
            elif rutf8._invalid_byte_3_of_4(ordch3):
                r, pos = errorhandler(errors, "utf8", "invalid continuation byte",
                    s, pos - 1, pos + 1)
                res.append(r)
                continue
            elif rutf8._invalid_byte_4_of_4(ordch4):
                r, pos = errorhandler(errors, "utf8", "invalid continuation byte",
                    s, pos - 1, pos + 2)
                res.append(r)
                continue

            pos += 3
            # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
            res.append(chr(ordch1))
            res.append(chr(ordch2))
            res.append(chr(ordch3))
            res.append(chr(ordch4))
            continuation_bytes += 3
            continue

        r, pos = errorhandler(errors, "utf8", "invalid start byte",
                s, pos - 1, pos)
        res.append(r)

    assert pos == end
    assert pos - continuation_bytes >= 0
    r = res.build()
    lgt, flag = rutf8.check_utf8(r, True)
    return r, pos, lgt, flag

hexdigits = "0123456789ABCDEFabcdef"

def hexescape(builder, s, pos, digits,
              encoding, errorhandler, message, errors):
    chr = 0
    if pos + digits > len(s):
        endinpos = pos
        while endinpos < len(s) and s[endinpos] in hexdigits:
            endinpos += 1
        res, pos = errorhandler(errors, encoding,
                                 message, s, pos-2, endinpos)
        size, flag = rutf8.check_utf8(res, True)
        builder.append(res)
    else:
        try:
            chr = r_uint(int(s[pos:pos+digits], 16))
        except ValueError:
            aaaa
            endinpos = pos
            while s[endinpos] in hexdigits:
                endinpos += 1
            res, pos = errorhandler(errors, encoding,
                                    message, s, pos-2, endinpos)
            builder.append(res)
        else:
            # when we get here, chr is a 32-bit unicode character
            if chr > 0x10ffff:
                UUU
                message = "illegal Unicode character"
                res, pos = errorhandler(errors, encoding,
                                        message, s, pos-2, pos+digits)
                builder.append(res)
            else:
                rutf8.unichr_as_utf8_append(builder, chr, True)
                if chr <= 0x7f:
                    flag = rutf8.FLAG_ASCII
                elif 0xd800 <= chr <= 0xdfff:
                    flag = rutf8.FLAG_HAS_SURROGATES
                else:
                    flag = rutf8.FLAG_REGULAR
                pos += digits
                size = 1

    return pos, size, flag

def str_decode_unicode_escape(s, errors, final, errorhandler, ud_handler):
    size = len(s)
    if size == 0:
        return '', 0, 0, rutf8.FLAG_ASCII

    flag = rutf8.FLAG_ASCII
    builder = StringBuilder(size)
    pos = 0
    outsize = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            if ord(ch) > 0x7F:
                rutf8.unichr_as_utf8_append(builder, ord(ch))
                flag = combine_flags(rutf8.FLAG_REGULAR, flag)
            else:
                builder.append(ch)
            pos += 1
            outsize += 1
            continue

        # - Escapes
        pos += 1
        if pos >= size:
            message = "\\ at end of string"
            res, pos = errorhandler(errors, "unicodeescape",
                                    message, s, pos-1, size)
            newsize, newflag = rutf8.check_utf8(res, True)
            outsize + newsize
            flag = combine_flags(flag, newflag)
            builder.append(res)
            continue

        ch = s[pos]
        pos += 1
        # \x escapes
        if ch == '\n': pass
        elif ch == '\\':
            builder.append('\\')
            outsize += 1
        elif ch == '\'':
            builder.append('\'')
            outsize += 1
        elif ch == '\"':
            builder.append('\"')
            outsize += 1
        elif ch == 'b' :
            builder.append('\b')
            outsize += 1
        elif ch == 'f' :
            builder.append('\f')
            outsize += 1
        elif ch == 't' :
            builder.append('\t')
            outsize += 1
        elif ch == 'n' :
            builder.append('\n')
            outsize += 1
        elif ch == 'r' :
            builder.append('\r')
            outsize += 1
        elif ch == 'v' :
            builder.append('\v')
            outsize += 1
        elif ch == 'a' :
            builder.append('\a')
            outsize += 1
        elif '0' <= ch <= '7':
            x = ord(ch) - ord('0')
            if pos < size:
                ch = s[pos]
                if '0' <= ch <= '7':
                    pos += 1
                    x = (x<<3) + ord(ch) - ord('0')
                    if pos < size:
                        ch = s[pos]
                        if '0' <= ch <= '7':
                            pos += 1
                            x = (x<<3) + ord(ch) - ord('0')
            outsize += 1
            if x >= 0x7F:
                rutf8.unichr_as_utf8_append(builder, x)
                flag = combine_flags(rutf8.FLAG_REGULAR, flag)
            else:
                builder.append(chr(x))
        # hex escapes
        # \xXX
        elif ch == 'x':
            digits = 2
            message = "truncated \\xXX escape"
            pos, newsize, newflag = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)
            flag = combine_flags(flag, newflag)
            outsize += newsize

        # \uXXXX
        elif ch == 'u':
            digits = 4
            message = "truncated \\uXXXX escape"
            pos, newsize, newflag = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)
            flag = combine_flags(flag, newflag)
            outsize += newsize

        #  \UXXXXXXXX
        elif ch == 'U':
            digits = 8
            message = "truncated \\UXXXXXXXX escape"
            pos, newsize, newflag = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)
            flag = combine_flags(flag, newflag)
            outsize += newsize

        # \N{name}
        elif ch == 'N' and ud_handler is not None:
            message = "malformed \\N character escape"
            look = pos

            if look < size and s[look] == '{':
                # look for the closing brace
                while look < size and s[look] != '}':
                    look += 1
                if look < size and s[look] == '}':
                    # found a name.  look it up in the unicode database
                    message = "unknown Unicode character name"
                    name = s[pos+1:look]
                    code = ud_handler.call(name)
                    if code < 0:
                        res, pos = errorhandler(errors, "unicodeescape",
                                                message, s, pos-1, look+1)
                        newsize, newflag = rutf8.check_utf8(res, True)
                        flag = combine_flags(flag, newflag)
                        outsize += newsize
                        builder.append(res)
                        continue
                    pos = look + 1
                    XXX
                    if code <= MAXUNICODE:
                        builder.append(UNICHR(code))
                    else:
                        code -= 0x10000L
                        builder.append(unichr(0xD800 + (code >> 10)))
                        builder.append(unichr(0xDC00 + (code & 0x03FF)))
                else:
                    YYY
                    res, pos = errorhandler(errors, "unicodeescape",
                                            message, s, pos-1, look+1)
                    builder.append(res)
            else:
                AAA
                res, pos = errorhandler(errors, "unicodeescape",
                                        message, s, pos-1, look+1)
                builder.append(res)
        else:
            builder.append('\\')
            builder.append(ch)
            outsize += 2

    return builder.build(), pos, outsize, flag

# ____________________________________________________________
# Raw unicode escape

def str_decode_raw_unicode_escape(s, errors, final=False,
                                  errorhandler=None):
    size = len(s)
    if size == 0:
        return '', 0, 0, rutf8.FLAG_ASCII

    result = StringBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            rutf8.unichr_as_utf8_append(result, ord(ch), True)
            pos += 1
            continue

        # \u-escapes are only interpreted iff the number of leading
        # backslashes is odd
        bs = pos
        while pos < size:
            pos += 1
            if pos == size or s[pos] != '\\':
                break
            result.append('\\')

        # we have a backslash at the end of the string, stop here
        if pos >= size:
            result.append('\\')
            break

        if ((pos - bs) & 1 == 0 or
            pos >= size or
            (s[pos] != 'u' and s[pos] != 'U')):
            result.append('\\')
            rutf8.unichr_as_utf8_append(result, ord(s[pos]), True)
            pos += 1
            continue

        digits = 4 if s[pos] == 'u' else 8
        message = "truncated \\uXXXX"
        pos += 1
        pos = hexescape(result, s, pos, digits,
                        "rawunicodeescape", errorhandler, message, errors)

    r = result.build()
    lgt, flag = rutf8.check_utf8(r, True)
    return r, pos, lgt, flag


TABLE = '0123456789abcdef'

def raw_unicode_escape_helper(result, char):
    if char >= 0x10000 or char < 0:
        result.append("\\U")
        zeros = 8
    elif char >= 0x100:
        result.append("\\u")
        zeros = 4
    else:
        result.append("\\x")
        zeros = 2
    for i in range(zeros-1, -1, -1):
        result.append(TABLE[(char >> (4 * i)) & 0x0f])

def utf8_encode_raw_unicode_escape(s, errors, errorhandler=None):
    # errorhandler is not used: this function cannot cause Unicode errors
    size = len(s)
    if size == 0:
        return ''
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        oc = ord(s[pos])

        if oc < 0x100:
            result.append(chr(oc))
        else:
            raw_unicode_escape_helper(result, oc)
        pos += 1

    return result.build()


# ____________________________________________________________
# utf-7

# Three simple macros defining base-64

def _utf7_IS_BASE64(oc):
    "Is c a base-64 character?"
    c = chr(oc)
    return c.isalnum() or c == '+' or c == '/'
def _utf7_TO_BASE64(n):
    "Returns the base-64 character of the bottom 6 bits of n"
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[n & 0x3f]
def _utf7_FROM_BASE64(c):
    "given that c is a base-64 character, what is its base-64 value?"
    if c >= 'a':
        return ord(c) - 71
    elif c >= 'A':
        return ord(c) - 65
    elif c >= '0':
        return ord(c) + 4
    elif c == '+':
        return 62
    else: # c == '/'
        return 63

def _utf7_DECODE_DIRECT(oc):
    return oc <= 127 and oc != ord('+')

# The UTF-7 encoder treats ASCII characters differently according to
# whether they are Set D, Set O, Whitespace, or special (i.e. none of
# the above).  See RFC2152.  This array identifies these different
# sets:
# 0 : "Set D"
#      alphanumeric and '(),-./:?
# 1 : "Set O"
#     !"#$%&*;<=>@[]^_`{|}
# 2 : "whitespace"
#     ht nl cr sp
# 3 : special (must be base64 encoded)
#     everything else (i.e. +\~ and non-printing codes 0-8 11-12 14-31 127)

utf7_category = [
#  nul soh stx etx eot enq ack bel bs  ht  nl  vt  np  cr  so  si
    3,  3,  3,  3,  3,  3,  3,  3,  3,  2,  2,  3,  3,  2,  3,  3,
#  dle dc1 dc2 dc3 dc4 nak syn etb can em  sub esc fs  gs  rs  us
    3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,
#  sp   !   "   #   $   %   &   '   (   )   *   +   ,   -   .   /
    2,  1,  1,  1,  1,  1,  1,  0,  0,  0,  1,  3,  0,  0,  0,  0,
#   0   1   2   3   4   5   6   7   8   9   :   ;   <   =   >   ?
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  0,
#   @   A   B   C   D   E   F   G   H   I   J   K   L   M   N   O
    1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
#   P   Q   R   S   T   U   V   W   X   Y   Z   [   \   ]   ^   _
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  3,  1,  1,  1,
#   `   a   b   c   d   e   f   g   h   i   j   k   l   m   n   o
    1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
#   p   q   r   s   t   u   v   w   x   y   z   {   |   }   ~  del
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  3,  3,
]

# ENCODE_DIRECT: this character should be encoded as itself.  The
# answer depends on whether we are encoding set O as itself, and also
# on whether we are encoding whitespace as itself.  RFC2152 makes it
# clear that the answers to these questions vary between
# applications, so this code needs to be flexible.

def _utf7_ENCODE_DIRECT(oc, directO, directWS):
    return(oc < 128 and oc > 0 and
           (utf7_category[oc] == 0 or
            (directWS and utf7_category[oc] == 2) or
            (directO and utf7_category[oc] == 1)))

def _utf7_ENCODE_CHAR(result, oc, base64bits, base64buffer):
    if oc >= 0x10000:
        # code first surrogate
        base64bits += 16
        base64buffer = (base64buffer << 16) | 0xd800 | ((oc-0x10000) >> 10)
        while base64bits >= 6:
            result.append(_utf7_TO_BASE64(base64buffer >> (base64bits-6)))
            base64bits -= 6
        # prepare second surrogate
        oc = 0xDC00 | ((oc-0x10000) & 0x3FF)
    base64bits += 16
    base64buffer = (base64buffer << 16) | oc
    while base64bits >= 6:
        result.append(_utf7_TO_BASE64(base64buffer >> (base64bits-6)))
        base64bits -= 6
    return base64bits, base64buffer

def str_decode_utf_7(s, errors, final=False,
                     errorhandler=None):
    size = len(s)
    if size == 0:
        return '', 0, 0, rutf8.FLAG_ASCII

    inShift = False
    base64bits = 0
    base64buffer = 0
    surrogate = 0
    outsize = 0

    result = StringBuilder(size)
    pos = 0
    shiftOutStartPos = 0
    flag = rutf8.FLAG_ASCII
    startinpos = 0
    while pos < size:
        ch = s[pos]

        if inShift: # in a base-64 section
            if _utf7_IS_BASE64(ord(ch)): #consume a base-64 character
                base64buffer = (base64buffer << 6) | _utf7_FROM_BASE64(ch)
                base64bits += 6
                pos += 1

                if base64bits >= 16:
                    # enough bits for a UTF-16 value
                    outCh = base64buffer >> (base64bits - 16)
                    base64bits -= 16
                    base64buffer &= (1 << base64bits) - 1 # clear high bits
                    assert outCh <= 0xffff
                    if surrogate:
                        # expecting a second surrogate
                        if outCh >= 0xDC00 and outCh <= 0xDFFF:
                            xxxx
                            result.append(
                                UNICHR((((surrogate & 0x3FF)<<10) |
                                        (outCh & 0x3FF)) + 0x10000))
                            surrogate = 0
                            continue
                        else:
                            YYYY
                            result.append(unichr(surrogate))
                            surrogate = 0
                            # Not done with outCh: falls back to next line
                    if outCh >= 0xD800 and outCh <= 0xDBFF:
                        # first surrogate
                        surrogate = outCh
                    else:
                        flag = combine_flags(flag, rutf8.unichr_to_flag(outCh))
                        outsize += 1
                        rutf8.unichr_as_utf8_append(result, outCh, True)

            else:
                # now leaving a base-64 section
                inShift = False

                if base64bits > 0: # left-over bits
                    if base64bits >= 6:
                        # We've seen at least one base-64 character
                        aaa
                        pos += 1
                        msg = "partial character in shift sequence"
                        res, pos = errorhandler(errors, 'utf7',
                                                msg, s, pos-1, pos)
                        result.append(res)
                        continue
                    else:
                        # Some bits remain; they should be zero
                        if base64buffer != 0:
                            bbb
                            pos += 1
                            msg = "non-zero padding bits in shift sequence"
                            res, pos = errorhandler(errors, 'utf7',
                                                    msg, s, pos-1, pos)
                            result.append(res)
                            continue

                if surrogate and _utf7_DECODE_DIRECT(ord(ch)):
                    outsize += 1
                    flag = rutf8.FLAG_HAS_SURROGATES
                    rutf8.unichr_as_utf8_append(result, surrogate, True)
                surrogate = 0

                if ch == '-':
                    # '-' is absorbed; other terminating characters are
                    # preserved
                    pos += 1

        elif ch == '+':
            startinpos = pos
            pos += 1 # consume '+'
            if pos < size and s[pos] == '-': # '+-' encodes '+'
                pos += 1
                result.append('+')
                outsize += 1
            else: # begin base64-encoded section
                inShift = 1
                surrogate = 0
                shiftOutStartPos = result.getlength()
                base64bits = 0
                base64buffer = 0

        elif _utf7_DECODE_DIRECT(ord(ch)): # character decodes at itself
            result.append(ch)
            outsize += 1
            pos += 1
        else:
            yyy
            startinpos = pos
            pos += 1
            msg = "unexpected special character"
            res, pos = errorhandler(errors, 'utf7', msg, s, pos-1, pos)
            result.append(res)

    # end of string
    final_length = result.getlength()
    if inShift and final: # in shift sequence, no more to follow
        # if we're in an inconsistent state, that's an error
        inShift = 0
        if (surrogate or
            base64bits >= 6 or
            (base64bits > 0 and base64buffer != 0)):
            msg = "unterminated shift sequence"
            res, pos = errorhandler(errors, 'utf7', msg, s, shiftOutStartPos, pos)
            reslen, resflags = rutf8.check_utf8(res, True)
            outsize += reslen
            flag = combine_flags(flag, resflags)
            result.append(res)
            final_length = result.getlength()
    elif inShift:
        pos = startinpos
        final_length = shiftOutStartPos # back off output

    assert final_length >= 0
    return result.build()[:final_length], pos, outsize, flag

def utf8_encode_utf_7(s, errors, errorhandler=None):
    size = len(s)
    if size == 0:
        return ''
    result = StringBuilder(size)

    encodeSetO = encodeWhiteSpace = False

    inShift = False
    base64bits = 0
    base64buffer = 0

    pos = 0
    while pos < size:
        oc = rutf8.codepoint_at_pos(s, pos)
        if not inShift:
            if oc == ord('+'):
                result.append('+-')
            elif _utf7_ENCODE_DIRECT(oc, not encodeSetO, not encodeWhiteSpace):
                result.append(chr(oc))
            else:
                result.append('+')
                inShift = True
                base64bits, base64buffer = _utf7_ENCODE_CHAR(
                    result, oc, base64bits, base64buffer)
        else:
            if _utf7_ENCODE_DIRECT(oc, not encodeSetO, not encodeWhiteSpace):
                # shifting out
                if base64bits: # output remaining bits
                    result.append(_utf7_TO_BASE64(base64buffer << (6-base64bits)))
                    base64buffer = 0
                    base64bits = 0

                inShift = False
                ## Characters not in the BASE64 set implicitly unshift the
                ## sequence so no '-' is required, except if the character is
                ## itself a '-'
                if _utf7_IS_BASE64(oc) or oc == ord('-'):
                    result.append('-')
                result.append(chr(oc))
            else:
                base64bits, base64buffer = _utf7_ENCODE_CHAR(
                    result, oc, base64bits, base64buffer)
        pos = rutf8.next_codepoint_pos(s, pos)

    if base64bits:
        result.append(_utf7_TO_BASE64(base64buffer << (6 - base64bits)))
    if inShift:
        result.append('-')

    return result.build()

# ____________________________________________________________
# utf-16

BYTEORDER = sys.byteorder
BYTEORDER2 = BYTEORDER[0] + 'e'      # either "le" or "be"
assert BYTEORDER2 in ('le', 'be')

def str_decode_utf_16(s, errors, final=True,
                      errorhandler=None):
    result, c, lgt, flag, _ = str_decode_utf_16_helper(s, errors, final,
                                                         errorhandler, "native")
    return result, c, lgt, flag

def str_decode_utf_16_be(s, errors, final=True,
                        errorhandler=None):
    result, c, lgt, flag, _ = str_decode_utf_16_helper(s, errors, final,
                                                         errorhandler, "big")
    return result, c, lgt, flag

def str_decode_utf_16_le(s, errors, final=True,
                         errorhandler=None):
    result, c, lgt, flag, _ = str_decode_utf_16_helper(s, errors, final,
                                                         errorhandler, "little")
    return result, c, lgt, flag

def str_decode_utf_16_helper(s, errors, final=True,
                             errorhandler=None,
                             byteorder="native",
                             public_encoding_name='utf16'):
    size = len(s)
    bo = 0

    if BYTEORDER == 'little':
        ihi = 1
        ilo = 0
    else:
        ihi = 0
        ilo = 1

    #  Check for BOM marks (U+FEFF) in the input and adjust current
    #  byte order setting accordingly. In native mode, the leading BOM
    #  mark is skipped, in all other modes, it is copied to the output
    #  stream as-is (giving a ZWNBSP character).
    pos = 0
    if byteorder == 'native':
        if size >= 2:
            bom = (ord(s[ihi]) << 8) | ord(s[ilo])
            if BYTEORDER == 'little':
                if bom == 0xFEFF:
                    pos += 2
                    bo = -1
                elif bom == 0xFFFE:
                    pos += 2
                    bo = 1
            else:
                if bom == 0xFEFF:
                    pos += 2
                    bo = 1
                elif bom == 0xFFFE:
                    pos += 2
                    bo = -1
    elif byteorder == 'little':
        bo = -1
    else:
        bo = 1
    if size == 0:
        return u'', 0, bo
    if bo == -1:
        # force little endian
        ihi = 1
        ilo = 0

    elif bo == 1:
        # force big endian
        ihi = 0
        ilo = 1

    result = StringBuilder(size // 2)

    #XXX I think the errors are not correctly handled here
    while pos < size:
        # remaining bytes at the end? (size should be even)
        if len(s) - pos < 2:
            if not final:
                break
            r, pos = errorhandler(errors, public_encoding_name,
                                  "truncated data",
                                  s, pos, len(s))
            result.append(r)
            if len(s) - pos < 2:
                break
        ch = (ord(s[pos + ihi]) << 8) | ord(s[pos + ilo])
        pos += 2
        if ch < 0xD800 or ch > 0xDFFF:
            rutf8.unichr_as_utf8_append(result, ch)
            continue
        # UTF-16 code pair:
        if len(s) - pos < 2:
            pos -= 2
            if not final:
                break
            errmsg = "unexpected end of data"
            r, pos = errorhandler(errors, public_encoding_name,
                                  errmsg, s, pos, len(s))
            result.append(r)
            if len(s) - pos < 2:
                break
        elif 0xD800 <= ch <= 0xDBFF:
            ch2 = (ord(s[pos+ihi]) << 8) | ord(s[pos+ilo])
            pos += 2
            if 0xDC00 <= ch2 <= 0xDFFF:
                ch = (((ch & 0x3FF)<<10) | (ch2 & 0x3FF)) + 0x10000
                rutf8.unichr_as_utf8_append(result, ch)
                continue
            else:
                r, pos = errorhandler(errors, public_encoding_name,
                                      "illegal UTF-16 surrogate",
                                      s, pos - 4, pos - 2)
                result.append(r)
        else:
            r, pos = errorhandler(errors, public_encoding_name,
                                  "illegal encoding",
                                  s, pos - 2, pos)
            result.append(r)
    r = result.build()
    lgt, flag = rutf8.check_utf8(r, True)
    return result.build(), pos, lgt, flag, bo

def _STORECHAR(result, CH, byteorder):
    hi = chr(((CH) >> 8) & 0xff)
    lo = chr((CH) & 0xff)
    if byteorder == 'little':
        result.append(lo)
        result.append(hi)
    else:
        result.append(hi)
        result.append(lo)

def unicode_encode_utf_16_helper(s, errors,
                                 errorhandler=None,
                                 allow_surrogates=True,
                                 byteorder='little',
                                 public_encoding_name='utf16'):
    size = len(s)
    if size == 0:
        if byteorder == 'native':
            result = StringBuilder(2)
            _STORECHAR(result, 0xFEFF, BYTEORDER)
            return result.build()
        return ""

    result = StringBuilder(size * 2 + 2)
    if byteorder == 'native':
        _STORECHAR(result, 0xFEFF, BYTEORDER)
        byteorder = BYTEORDER

    pos = 0
    while pos < size:
        ch = rutf8.codepoint_at_pos(s, pos)
        pos = rutf8.next_codepoint_pos(s, pos)

        if ch < 0xD800:
            _STORECHAR(result, ch, byteorder)
        elif ch >= 0x10000:
            _STORECHAR(result, 0xD800 | ((ch-0x10000) >> 10), byteorder)
            _STORECHAR(result, 0xDC00 | ((ch-0x10000) & 0x3FF), byteorder)
        elif ch >= 0xE000 or allow_surrogates:
            _STORECHAR(result, ch, byteorder)
        else:
            ru, pos = errorhandler(errors, public_encoding_name,
                                   'surrogates not allowed',
                                    s, pos-1, pos)
            xxx
            #if rs is not None:
            #    # py3k only
            #    if len(rs) % 2 != 0:
            #        errorhandler('strict', public_encoding_name,
            #                     'surrogates not allowed',
            #                     s, pos-1, pos)
            #    result.append(rs)
            #    continue
            for ch in ru:
                if ord(ch) < 0xD800:
                    _STORECHAR(result, ord(ch), byteorder)
                else:
                    errorhandler('strict', public_encoding_name,
                                 'surrogates not allowed',
                                 s, pos-1, pos)
            continue

    return result.build()

def utf8_encode_utf_16(s, errors,
                          errorhandler=None,
                          allow_surrogates=True):
    return unicode_encode_utf_16_helper(s, errors, errorhandler,
                                        allow_surrogates, "native")

def utf8_encode_utf_16_be(s, errors,
                             errorhandler=None,
                             allow_surrogates=True):
    return unicode_encode_utf_16_helper(s, errors, errorhandler,
                                        allow_surrogates, "big")

def utf8_encode_utf_16_le(s, errors,
                             errorhandler=None,
                             allow_surrogates=True):
    return unicode_encode_utf_16_helper(s, errors, errorhandler,
                                        allow_surrogates, "little")

# ____________________________________________________________
# utf-32

def str_decode_utf_32(s, errors, final=True,
                      errorhandler=None):
    result, c, lgt, flag, _ = str_decode_utf_32_helper(s, errors, final,
                                                         errorhandler, "native")
    return result, c, lgt, flag

def str_decode_utf_32_be(s, errors, final=True,
                         errorhandler=None):
    result, c, lgt, flag, _ = str_decode_utf_32_helper(s, errors, final,
                                                         errorhandler, "big")
    return result, c, lgt, flag

def str_decode_utf_32_le(s, errors, final=True,
                         errorhandler=None):
    result, c, lgt, flag, _ = str_decode_utf_32_helper(s, errors, final,
                                                         errorhandler, "little")
    return result, c, lgt, flag

BOM32_DIRECT  = intmask(0x0000FEFF)
BOM32_REVERSE = intmask(0xFFFE0000)

def str_decode_utf_32_helper(s, errors, final=True,
                             errorhandler=None,
                             byteorder="native",
                             public_encoding_name='utf32'):
    bo = 0
    size = len(s)

    if BYTEORDER == 'little':
        iorder = [0, 1, 2, 3]
    else:
        iorder = [3, 2, 1, 0]

    #  Check for BOM marks (U+FEFF) in the input and adjust current
    #  byte order setting accordingly. In native mode, the leading BOM
    #  mark is skipped, in all other modes, it is copied to the output
    #  stream as-is (giving a ZWNBSP character).
    pos = 0
    if byteorder == 'native':
        if size >= 4:
            bom = intmask(
                (ord(s[iorder[3]]) << 24) | (ord(s[iorder[2]]) << 16) |
                (ord(s[iorder[1]]) << 8)  | ord(s[iorder[0]]))
            if BYTEORDER == 'little':
                if bom == BOM32_DIRECT:
                    pos += 4
                    bo = -1
                elif bom == BOM32_REVERSE:
                    pos += 4
                    bo = 1
            else:
                if bom == BOM32_DIRECT:
                    pos += 4
                    bo = 1
                elif bom == BOM32_REVERSE:
                    pos += 4
                    bo = -1
    elif byteorder == 'little':
        bo = -1
    else:
        bo = 1
    if size == 0:
        return u'', 0, bo
    if bo == -1:
        # force little endian
        iorder = [0, 1, 2, 3]

    elif bo == 1:
        # force big endian
        iorder = [3, 2, 1, 0]

    result = StringBuilder(size // 4)

    while pos < size:
        # remaining bytes at the end? (size should be divisible by 4)
        if len(s) - pos < 4:
            if not final:
                break
            r, pos = errorhandler(errors, public_encoding_name,
                                  "truncated data",
                                  s, pos, len(s))
            result.append(r)
            if len(s) - pos < 4:
                break
            continue
        ch = ((ord(s[pos + iorder[3]]) << 24) | (ord(s[pos + iorder[2]]) << 16) |
              (ord(s[pos + iorder[1]]) << 8)  | ord(s[pos + iorder[0]]))
        if ch >= 0x110000:
            r, pos = errorhandler(errors, public_encoding_name,
                                  "codepoint not in range(0x110000)",
                                  s, pos, len(s))
            result.append(r)
            continue

        rutf8.unichr_as_utf8_append(result, ch)
        pos += 4
    r = result.build()
    lgt, flag = rutf8.check_utf8(r, True)
    return r, pos, lgt, flag, bo

def _STORECHAR32(result, CH, byteorder):
    c0 = chr(((CH) >> 24) & 0xff)
    c1 = chr(((CH) >> 16) & 0xff)
    c2 = chr(((CH) >> 8) & 0xff)
    c3 = chr((CH) & 0xff)
    if byteorder == 'little':
        result.append(c3)
        result.append(c2)
        result.append(c1)
        result.append(c0)
    else:
        result.append(c0)
        result.append(c1)
        result.append(c2)
        result.append(c3)

def unicode_encode_utf_32_helper(s, errors,
                                 errorhandler=None,
                                 allow_surrogates=True,
                                 byteorder='little',
                                 public_encoding_name='utf32'):
    size = len(s)
    if size == 0:
        if byteorder == 'native':
            result = StringBuilder(4)
            _STORECHAR32(result, 0xFEFF, BYTEORDER)
            return result.build()
        return ""

    result = StringBuilder(size * 4 + 4)
    if byteorder == 'native':
        _STORECHAR32(result, 0xFEFF, BYTEORDER)
        byteorder = BYTEORDER

    pos = 0
    while pos < size:
        ch = rutf8.codepoint_at_pos(s, pos)
        pos = rutf8.next_codepoint_pos(s, pos)
        ch2 = 0
        if not allow_surrogates and 0xD800 <= ch < 0xE000:
            ru, pos = errorhandler(errors, public_encoding_name,
                                        'surrogates not allowed',
                                        s, pos-1, pos)
            XXX
            if rs is not None:
                # py3k only
                if len(rs) % 4 != 0:
                    errorhandler('strict', public_encoding_name,
                                    'surrogates not allowed',
                                    s, pos-1, pos)
                result.append(rs)
                continue
            for ch in ru:
                if ord(ch) < 0xD800:
                    _STORECHAR32(result, ord(ch), byteorder)
                else:
                    errorhandler('strict', public_encoding_name,
                                    'surrogates not allowed',
                                    s, pos-1, pos)
            continue
        _STORECHAR32(result, ch, byteorder)

    return result.build()

def utf8_encode_utf_32(s, errors,
                          errorhandler=None, allow_surrogates=True):
    return unicode_encode_utf_32_helper(s, errors, errorhandler,
                                        allow_surrogates, "native")

def utf8_encode_utf_32_be(s, errors,
                             errorhandler=None, allow_surrogates=True):
    return unicode_encode_utf_32_helper(s, errors, errorhandler,
                                        allow_surrogates, "big")

def utf8_encode_utf_32_le(s, errors,
                             errorhandler=None, allow_surrogates=True):
    return unicode_encode_utf_32_helper(s, errors, errorhandler,
                                        allow_surrogates, "little")
