from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import specialize
from rpython.rlib import runicode, rutf8
from rpython.rlib.rarithmetic import r_uint
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

def hexescape(builder, s, pos, digits,
              encoding, errorhandler, message, errors):
    chr = 0
    if pos + digits > len(s):
        endinpos = pos
        while endinpos < len(s) and s[endinpos] in hexdigits:
            endinpos += 1
        uuu
        res, size, pos = errorhandler(errors, encoding,
                                message, s, pos-2, endinpos)
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

# These functions take and return unwrapped rpython strings and unicodes
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
    # XXX pick better length, maybe
    # XXX that guy does not belong in runicode (nor in rutf8)
    result_u, consumed = runicode.str_decode_raw_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=DecodeWrapper(decode_error_handler(space)).handle)
    # XXX argh.  we want each surrogate to be encoded separately
    utf8 = ''.join([u.encode('utf8') for u in result_u])
    if rutf8.first_non_ascii_char(utf8) == -1:
        flag = rutf8.FLAG_ASCII
    elif _has_surrogate(result_u):
        flag = rutf8.FLAG_HAS_SURROGATES
    else:
        flag = rutf8.FLAG_REGULAR
    return utf8, len(result_u), flag

def check_ascii_or_raise(space, string):
    try:
        rutf8.check_ascii(string)
    except rutf8.CheckError as e:
        decode_error_handler(space)('strict', 'ascii',
                                    'ordinal not in range(128)', string,
                                    e.pos, e.pos + 1)
        assert False, "unreachable"

def check_utf8_or_raise(space, string):
    # Surrogates are accepted and not treated specially at all.
    # If there happen to be two 3-bytes encoding a pair of surrogates,
    # you still get two surrogate unicode characters in the result.
    # These are the Python2 rules; Python3 differs.
    try:
        length, flag = rutf8.check_utf8(string, allow_surrogates=True)
    except rutf8.CheckError as e:
        # convert position into unicode position
        lgt, flags = rutf8.check_utf8(string, True, stop=e.pos)
        decode_error_handler(space)('strict', 'utf8', 'invalid utf-8', string,
                                    lgt, lgt + 1)
        assert False, "unreachable"
    return length, flag

def encode_utf8(space, uni):
    # DEPRECATED
    # Note that this function never raises UnicodeEncodeError,
    # since surrogates are allowed, either paired or lone.
    # A paired surrogate is considered like the non-BMP character
    # it stands for.  These are the Python2 rules; Python3 differs.
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=None,
        allow_surrogates=True)

def decode_utf8(space, s):
    # DEPRECATED
    return (s, check_utf8_or_raise(space, s))

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

# XXX wrappers, think about speed

class DecodeWrapper(object):
    def __init__(self, handler):
        self.orig = handler

    def handle(self, errors, encoding, msg, s, pos, endpos):
        return self.orig(errors, encoding, msg, s, pos, endpos)

class EncodeWrapper(object):
    def __init__(self, handler):
        self.orig = handler

    def handle(self, errors, encoding, msg, s, pos, endpos):
        return self.orig(errors, encoding, msg, s.encode("utf8"), pos, endpos)

#def str_decode_unicode_escape(s, slen, errors, final, errorhandler, ud_handler):
#    w = DecodeWrapper(errorhandler)
#    u, pos = runicode.str_decode_unicode_escape(s, slen, errors, final,
#                                                w.handle,
#                                                ud_handler)
#    return u.encode('utf8'), pos, len(u), _get_flag(u)

def setup_new_encoders_legacy(encoding):
    encoder_name = 'utf8_encode_' + encoding
    encoder_call_name = 'unicode_encode_' + encoding
    decoder_name = 'str_decode_' + encoding
    def encoder(utf8, utf8len, errors, errorhandler):
        u = utf8.decode("utf8")
        w = EncodeWrapper(errorhandler)
        return getattr(runicode, encoder_call_name)(u, len(u), errors,
                       w.handle)
    def decoder(s, slen, errors, final, errorhandler):
        w = DecodeWrapper((errorhandler))
        u, pos = getattr(runicode, decoder_name)(s, slen, errors, final, w.handle)
        return u.encode('utf8'), pos, len(u), _get_flag(u)
    encoder.__name__ = encoder_name
    decoder.__name__ = decoder_name
    if encoder_name not in globals():
        globals()[encoder_name] = encoder
    if decoder_name not in globals():
        globals()[decoder_name] = decoder

def setup():
    for encoding in ['raw_unicode_escape',
                     'utf_16', 'utf_16_le', 'utf_16_be', 'utf_32_le', 'utf_32',
                     'utf_32_be', 'latin_1', 'unicode_internal']:
        setup_new_encoders_legacy(encoding)

setup()

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

# some irregular interfaces
def str_decode_utf8(s, slen, errors, final, errorhandler):
    xxxx

    u, pos = runicode.str_decode_utf_8_impl(s, slen, errors, final, w.handle,
        runicode.allow_surrogate_by_default)
    return u.encode('utf8'), pos, len(u), _get_flag(u)

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
            xxx
            result.append(unichr(ord(ch)))
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
            xxxx
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
