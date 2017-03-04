
from rpython.rlib.rstring import StringBuilder
from rpython.rlib import runicode, jit

def unichr_as_utf8(code):
    """ Encode code (numeric value) as utf8 encoded string
    """
    if code < 0:
        raise ValueError
    lgt = 1
    if code >= runicode.MAXUNICODE:
        lgt = 2
    if code < 0x80:
        # Encode ASCII
        return chr(code), 1
    if code < 0x0800:
        # Encode Latin-1
        return chr((0xc0 | (code >> 6))) + chr((0x80 | (code & 0x3f))), lgt
    if code < 0x10000:
        return (chr((0xe0 | (code >> 12))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f)))), lgt
    if code < 0x10ffff:
        return (chr((0xf0 | (code >> 18))) +
                chr((0x80 | ((code >> 12) & 0x3f))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f)))), lgt
    raise ValueError

def unichr_as_utf8_append(builder, code):
    """ Encode code (numeric value) as utf8 encoded string
    """
    if code < 0:
        raise ValueError
    lgt = 1
    if code >= runicode.MAXUNICODE:
        lgt = 2
    if code < 0x80:
        # Encode ASCII
        builder.append(chr(code))
        return 1
    if code < 0x0800:
        # Encode Latin-1
        builder.append(chr((0xc0 | (code >> 6))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return lgt
    if code < 0x10000:
        builder.append(chr((0xe0 | (code >> 12))))
        builder.append(chr((0x80 | ((code >> 6) & 0x3f))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return lgt
    if code < 0x10ffff:
        builder.append(chr((0xf0 | (code >> 18))))
        builder.append(chr((0x80 | ((code >> 12) & 0x3f))))
        builder.append(chr((0x80 | ((code >> 6) & 0x3f))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return lgt
    raise ValueError

# note - table lookups are really slow. Measured on various elements of obama
#        chinese wikipedia, they're anywhere between 10% and 30% slower.
#        In extreme cases (small, only chinese text), they're 40% slower

def next_codepoint_pos(code, pos):
    """ Gives the position of the next codepoint after pos, -1
    if it's the last one (assumes valid utf8)
    """
    chr1 = ord(code[pos])
    if chr1 < 0x80:
        return pos + 1
    if 0xC2 >= chr1 <= 0xDF:
        return pos + 2
    if chr1 >= 0xE0 and chr1 <= 0xEF:
        return pos + 3
    return pos + 4

def prev_codepoint_pos(code, pos):
    """ Gives the position of the previous codepoint
    """
    chr1 = ord(code[pos])
    if chr1 < 0x80:
        return pos - 1
    while ord(code[pos]) & 0xC0 == 0xC0:
        pos -= 1
    return pos

def compute_length_utf8(s):
    pos = 0
    lgt = 0
    while pos < len(s):
        pos = next_codepoint_pos(s, pos)
        lgt += 1
    return lgt

def codepoint_at_pos(code, pos):
    """ Give a codepoint in code at pos - assumes valid utf8, no checking!
    """
    ordch1 = ord(code[pos])
    if ordch1 < 0x80:
        return ordch1

    n = ord(runicode._utf8_code_length[ordch1 - 0x80])
    if n == 2:
        ordch2 = ord(code[pos+1])
        # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
        return (((ordch1 & 0x1F) << 6) +    # 0b00011111
                 (ordch2 & 0x3F))           # 0b00111111
    elif n == 3:
        ordch2 = ord(code[pos+1])
        ordch3 = ord(code[pos+2])
        # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x0F) << 12) +     # 0b00001111
                ((ordch2 & 0x3F) << 6) +      # 0b00111111
                (ordch3 & 0x3F))              # 0b00111111
    elif n == 4:
        ordch2 = ord(code[pos+1])
        ordch3 = ord(code[pos+2])
        ordch4 = ord(code[pos+3])
        # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x07) << 18) +      # 0b00000111
                ((ordch2 & 0x3F) << 12) +      # 0b00111111
                ((ordch3 & 0x3F) << 6) +       # 0b00111111
                (ordch4 & 0x3F))               # 0b00111111
    assert False, "unreachable"

class AsciiCheckError(Exception):
    def __init__(self, pos):
        self.pos = pos

def check_ascii(s, size=-1):
    if size == -1:
        size = len(s)
    for i in range(0, size):
        if ord(s[i]) & 0x80:
            raise AsciiCheckError(i)

def utf8_encode_ascii(s, errors, encoding, msg, errorhandler):
    res = StringBuilder(len(s))
    u_pos = 0
    pos = 0
    while pos < len(s):
        chr1 = s[pos]
        if ord(chr1) < 0x80:
            res.append(chr1)
        else:
            repl, _, _, _ = errorhandler(errors, encoding, msg, s, u_pos, u_pos + 1)
            res.append(repl)
        u_pos += 1
        pos = next_codepoint_pos(s, pos)
    return res.build()

def str_decode_ascii(s, size, errors, errorhandler):
    # ASCII is equivalent to the first 128 ordinals in Unicode.
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        c = s[pos]
        if ord(c) < 128:
            result.append(c)
        else:
            r, _, _ = errorhandler(errors, "ascii", "ordinal not in range(128)",
                                   s,  pos, pos + 1)
            result.append(r)
        pos += 1
    return result.build(), pos, -1

def check_newline_utf8(s, pos):
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

class Utf8CheckError(Exception):
    def __init__(self, msg, startpos, endpos):
        self.msg = msg
        self.startpos = startpos
        self.endpos = endpos

@jit.elidable
def str_check_utf8(s, size, final=False,
                   allow_surrogates=runicode.allow_surrogate_by_default):
    """ A simplified version of utf8 encoder - it only works with 'strict'
    error handling.
    """
    # XXX do the following in a cleaner way, e.g. via signature
    # NB. a bit messy because rtyper/rstr.py also calls the same
    # function.  Make sure we annotate for the args it passes, too
    #if NonConstant(False):
    #    s = NonConstant('?????')
    #    size = NonConstant(12345)
    #    errors = NonConstant('strict')
    #    final = NonConstant(True)
    #    errorhandler = ll_unicode_error_decode
    #    allow_surrogates = NonConstant(True)
    if size == 0:
        return 0, 0

    pos = 0
    lgt = 0
    while pos < size:
        ordch1 = ord(s[pos])
        # fast path for ASCII
        # XXX maybe use a while loop here
        if ordch1 < 0x80:
            lgt += 1
            pos += 1
            continue

        n = ord(runicode._utf8_code_length[ordch1 - 0x80])
        if pos + n > size:
            if not final:
                break
            # argh, this obscure block of code is mostly a copy of
            # what follows :-(
            charsleft = size - pos - 1 # either 0, 1, 2
            # note: when we get the 'unexpected end of data' we need
            # to care about the pos returned; it can be lower than size,
            # in case we need to continue running this loop
            if not charsleft:
                # there's only the start byte and nothing else
                raise Utf8CheckError('unexpected end of data', pos, pos + 1)
            ordch2 = ord(s[pos+1])
            if n == 3:
                # 3-bytes seq with only a continuation byte
                if runicode._invalid_byte_2_of_3(ordch1, ordch2, allow_surrogates):
                    # second byte invalid, take the first and continue
                    raise Utf8CheckError('invalid continuation byte', pos,
                                         pos + 1)
                else:
                    # second byte valid, but third byte missing
                    raise Utf8CheckError('unexpected end of data', pos, pos + 2)
            elif n == 4:
                # 4-bytes seq with 1 or 2 continuation bytes
                if runicode._invalid_byte_2_of_4(ordch1, ordch2):
                    # second byte invalid, take the first and continue
                    raise Utf8CheckError('invalid continuation byte', pos,
                                         pos + 1)
                elif charsleft == 2 and runicode._invalid_byte_3_of_4(ord(s[pos+2])):
                    # third byte invalid, take the first two and continue
                    raise Utf8CheckError('invalid continuation byte', pos,
                                         pos + 2)
                else:
                    # there's only 1 or 2 valid cb, but the others are missing
                    raise Utf8CheckError('unexpected end of data', pos,
                                         pos + charsleft + 1)
            raise AssertionError("unreachable")

        if n == 0:
            raise Utf8CheckError('invalid start byte', pos, pos + 1)
        elif n == 1:
            assert 0, "ascii should have gone through the fast path"

        elif n == 2:
            ordch2 = ord(s[pos+1])
            if runicode._invalid_byte_2_of_2(ordch2):
                raise Utf8CheckError('invalid continuation byte', pos,
                                     pos + 2)
            # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
            lgt += 1
            pos += 2

        elif n == 3:
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            if runicode._invalid_byte_2_of_3(ordch1, ordch2, allow_surrogates):
                raise Utf8CheckError('invalid continuation byte', pos,
                                     pos + 1)
            elif runicode._invalid_byte_3_of_3(ordch3):
                raise Utf8CheckError('invalid continuation byte', pos,
                                     pos + 2)
            # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
            lgt += 1
            pos += 3

        elif n == 4:
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            ordch4 = ord(s[pos+3])
            if runicode._invalid_byte_2_of_4(ordch1, ordch2):
                raise Utf8CheckError('invalid continuation byte', pos,
                                     pos + 1)
            elif runicode._invalid_byte_3_of_4(ordch3):
                raise Utf8CheckError('invalid continuation byte', pos,
                                     pos + 2)
            elif runicode._invalid_byte_4_of_4(ordch4):
                raise Utf8CheckError('invalid continuation byte', pos,
                                     pos + 3)
            # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
            c = (((ordch1 & 0x07) << 18) +      # 0b00000111
                 ((ordch2 & 0x3F) << 12) +      # 0b00111111
                 ((ordch3 & 0x3F) << 6) +       # 0b00111111
                 (ordch4 & 0x3F))               # 0b00111111
            if c <= runicode.MAXUNICODE:
                lgt += 1
            else:
                # append the two surrogates:
                lgt += 2
            pos += 4

    return pos, lgt
