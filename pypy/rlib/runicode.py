import sys
from pypy.rlib.bitmanipulation import splitter
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder
from pypy.rlib.rarithmetic import r_uint, intmask

if rffi.sizeof(lltype.UniChar) == 4:
    MAXUNICODE = 0x10ffff
else:
    MAXUNICODE = 0xffff
BYTEORDER = sys.byteorder

if MAXUNICODE > sys.maxunicode:
    # A version of unichr which allows codes outside the BMP
    # even on narrow unicode builds.
    # It will be used when interpreting code on top of a UCS2 CPython,
    # when sizeof(wchar_t) == 4.
    # Note that Python3 uses a similar implementation.
    def UNICHR(c):
        assert not we_are_translated()
        if c <= sys.maxunicode or c > MAXUNICODE:
            return unichr(c)
        else:
            c -= 0x10000
            return (unichr(0xD800 + (c >> 10)) +
                    unichr(0xDC00 + (c & 0x03FF)))
    UNICHR._flowspace_rewrite_directly_as_ = unichr
    # ^^^ NB.: for translation, it's essential to use this hack instead
    # of calling unichr() from UNICHR(), because unichr() detects if there
    # is a "try:except ValueError" immediately around it.

    def ORD(u):
        assert not we_are_translated()
        if isinstance(u, unicode) and len(u) == 2:
            ch1 = ord(u[0])
            ch2 = ord(u[1])
            if 0xD800 <= ch1 <= 0xDBFF and 0xDC00 <= ch2 <= 0xDFFF:
                return (((ch1 - 0xD800) << 10) | (ch2 - 0xDC00)) + 0x10000
        return ord(u)
    ORD._flowspace_rewrite_directly_as_ = ord

else:
    UNICHR = unichr
    ORD = ord


def raise_unicode_exception_decode(errors, encoding, msg, s,
                                   startingpos, endingpos):
    assert isinstance(s, str)
    raise UnicodeDecodeError(encoding, s, startingpos, endingpos, msg)

def raise_unicode_exception_encode(errors, encoding, msg, u,
                                   startingpos, endingpos):
    assert isinstance(u, unicode)
    raise UnicodeEncodeError(encoding, u, startingpos, endingpos, msg)

# ____________________________________________________________
# utf-8

utf8_code_length = [
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 0, 0
]

def str_decode_utf_8(s, size, errors, final=False,
                     errorhandler=None):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    if size == 0:
        return u'', 0

    result = UnicodeBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]
        ordch1 = ord(ch)
        if ordch1 < 0x80:
            result.append(unichr(ordch1))
            pos += 1
            continue

        n = utf8_code_length[ordch1]
        if pos + n > size:
            if not final:
                break
            else:
                r, pos = errorhandler(errors, "utf-8",
                                      "unexpected end of data", s,  pos, size)
                result.append(r)
                if pos + n > size:
                    break
        if n == 0:
            r, pos = errorhandler(errors, "utf-8", "unexpected code byte",
                                  s,  pos, pos + 1)
            result.append(r)
        elif n == 1:
            assert 0, "you can never get here"
        elif n == 2:
            # 110yyyyy 10zzzzzz   ====>  00000000 00000yyy yyzzzzzz

            ordch2 = ord(s[pos+1])
            z, two = splitter[6, 2](ordch2)
            y, six = splitter[5, 3](ordch1)
            assert six == 6
            if two != 2:
                r, pos = errorhandler(errors, "utf-8", "invalid data",
                                      s,  pos, pos + 2)
                result.append(r)
            else:
                c = (y << 6) + z
                if c < 0x80:
                    r, pos = errorhandler(errors, "utf-8", "illegal encoding",
                                          s,  pos, pos + 2)
                    result.append(r)
                else:
                    result.append(unichr(c))
                    pos += n
        elif n == 3:
            #  1110xxxx 10yyyyyy 10zzzzzz ====> 00000000 xxxxyyyy yyzzzzzz
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            z, two1 = splitter[6, 2](ordch3)
            y, two2 = splitter[6, 2](ordch2)
            x, fourteen = splitter[4, 4](ordch1)
            assert fourteen == 14
            if two1 != 2 or two2 != 2:
                r, pos = errorhandler(errors, "utf-8", "invalid data",
                                      s,  pos, pos + 3)
                result.append(r)
            else:
                c = (x << 12) + (y << 6) + z
                # Note: UTF-8 encodings of surrogates are considered
                # legal UTF-8 sequences;
                # XXX For wide builds (UCS-4) we should probably try
                #     to recombine the surrogates into a single code
                #     unit.
                if c < 0x0800:
                    r, pos = errorhandler(errors, "utf-8", "illegal encoding",
                                          s,  pos, pos + 3)
                    result.append(r)
                else:
                    result.append(unichr(c))
                    pos += n
        elif n == 4:
            # 11110www 10xxxxxx 10yyyyyy 10zzzzzz ====>
            # 000wwwxx xxxxyyyy yyzzzzzz
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            ordch4 = ord(s[pos+3])
            z, two1 = splitter[6, 2](ordch4)
            y, two2 = splitter[6, 2](ordch3)
            x, two3 = splitter[6, 2](ordch2)
            w, thirty = splitter[3, 5](ordch1)
            assert thirty == 30
            if two1 != 2 or two2 != 2 or two3 != 2:
                r, pos = errorhandler(errors, "utf-8", "invalid data",
                                      s,  pos, pos + 4)
                result.append(r)
            else:
                c = (w << 18) + (x << 12) + (y << 6) + z
                # minimum value allowed for 4 byte encoding
                # maximum value allowed for UTF-16
                if c < 0x10000 or c > 0x10ffff:
                    r, pos = errorhandler(errors, "utf-8", "illegal encoding",
                                          s,  pos, pos + 4)
                    result.append(r)
                else:
                    # convert to UTF-16 if necessary
                    if c <= MAXUNICODE:
                        result.append(UNICHR(c))
                    else:
                        # compute and append the two surrogates:
                        # translate from 10000..10FFFF to 0..FFFF
                        c -= 0x10000
                        # high surrogate = top 10 bits added to D800
                        result.append(unichr(0xD800 + (c >> 10)))
                        # low surrogate = bottom 10 bits added to DC00
                        result.append(unichr(0xDC00 + (c & 0x03FF)))
                    pos += n
        else:
            r, pos = errorhandler(errors, "utf-8",
                                  "unsupported Unicode code range",
                                  s,  pos, pos + n)
            result.append(r)

    return result.build(), pos

def _encodeUCS4(result, ch):
    # Encode UCS4 Unicode ordinals
    result.append((chr((0xf0 | (ch >> 18)))))
    result.append((chr((0x80 | ((ch >> 12) & 0x3f)))))
    result.append((chr((0x80 | ((ch >> 6) & 0x3f)))))
    result.append((chr((0x80 | (ch & 0x3f)))))

def unicode_encode_utf_8(s, size, errors, errorhandler=None):
    assert(size >= 0)
    result = StringBuilder(size)
    i = 0
    while i < size:
        ch = ord(s[i])
        i += 1
        if ch < 0x80:
            # Encode ASCII
            result.append(chr(ch))
        elif ch < 0x0800:
            # Encode Latin-1
            result.append(chr((0xc0 | (ch >> 6))))
            result.append(chr((0x80 | (ch & 0x3f))))
        else:
            # Encode UCS2 Unicode ordinals
            if ch < 0x10000:
                # Special case: check for high surrogate
                if 0xD800 <= ch <= 0xDBFF and i != size:
                    ch2 = ord(s[i])
                    # Check for low surrogate and combine the two to
                    # form a UCS4 value
                    if 0xDC00 <= ch2 <= 0xDFFF:
                        ch3 = ((ch - 0xD800) << 10 | (ch2 - 0xDC00)) + 0x10000
                        i += 1
                        _encodeUCS4(result, ch3)
                        continue
                # Fall through: handles isolated high surrogates
                result.append((chr((0xe0 | (ch >> 12)))))
                result.append((chr((0x80 | ((ch >> 6) & 0x3f)))))
                result.append((chr((0x80 | (ch & 0x3f)))))
                continue
            else:
                _encodeUCS4(result, ch)
    return result.build()

# ____________________________________________________________
# utf-16

def str_decode_utf_16(s, size, errors, final=True,
                      errorhandler=None):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "native")
    return result, length

def str_decode_utf_16_be(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "big")
    return result, length

def str_decode_utf_16_le(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "little")
    return result, length

def str_decode_utf_16_helper(s, size, errors, final=True,
                             errorhandler=None,
                             byteorder="native"):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
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

    result = UnicodeBuilder(size // 2)

    #XXX I think the errors are not correctly handled here
    while pos < size:
        # remaining bytes at the end? (size should be even)
        if len(s) - pos < 2:
            if not final:
                break
            r, pos = errorhandler(errors, 'utf-16', "truncated data",
                                  s, pos, len(s))
            result.append(r)
            if len(s) - pos < 2:
                break
        ch = (ord(s[pos + ihi]) << 8) | ord(s[pos + ilo])
        pos += 2
        if ch < 0xD800 or ch > 0xDFFF:
            result.append(unichr(ch))
            continue
        # UTF-16 code pair:
        if len(s) - pos < 2:
            if not final:
                break
            errmsg = "unexpected end of data"
            r, pos = errorhandler(errors, 'utf-16', errmsg, s, pos - 2, len(s))
            result.append(r)
            if len(s) - pos < 2:
                break
        elif 0xD800 <= ch <= 0xDBFF:
            ch2 = (ord(s[pos+ihi]) << 8) | ord(s[pos+ilo])
            pos += 2
            if 0xDC00 <= ch2 <= 0xDFFF:
                if MAXUNICODE < 65536:
                    result.append(unichr(ch))
                    result.append(unichr(ch2))
                else:
                    result.append(UNICHR((((ch & 0x3FF)<<10) |
                                           (ch2 & 0x3FF)) + 0x10000))
                continue
            else:
                r, pos = errorhandler(errors, 'utf-16',
                                      "illegal UTF-16 surrogate",
                                      s, pos - 4, pos - 2)
                result.append(r)
        else:
            r, pos = errorhandler(errors, 'utf-16',
                                  "illegal encoding",
                                  s, pos - 2, pos)
            result.append(r)
    return result.build(), pos, bo

def _STORECHAR(result, CH, byteorder):
    hi = chr(((CH) >> 8) & 0xff)
    lo = chr((CH) & 0xff)
    if byteorder == 'little':
        result.append(lo)
        result.append(hi)
    else:
        result.append(hi)
        result.append(lo)

def unicode_encode_utf_16_helper(s, size, errors,
                                 errorhandler=None,
                                 byteorder='little'):
    if size == 0:
        return ""

    result = StringBuilder(size * 2 + 2)
    if byteorder == 'native':
        _STORECHAR(result, 0xFEFF, BYTEORDER)
        byteorder = BYTEORDER

    i = 0
    while i < size:
        ch = ord(s[i])
        i += 1
        ch2 = 0
        if ch >= 0x10000:
            ch2 = 0xDC00 | ((ch-0x10000) & 0x3FF)
            ch  = 0xD800 | ((ch-0x10000) >> 10)

        _STORECHAR(result, ch, byteorder)
        if ch2:
            _STORECHAR(result, ch2, byteorder)

    return result.build()

def unicode_encode_utf_16(s, size, errors,
                          errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "native")


def unicode_encode_utf_16_be(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "big")


def unicode_encode_utf_16_le(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "little")


# ____________________________________________________________
# utf-32

def str_decode_utf_32(s, size, errors, final=True,
                      errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(s, size, errors, final,
                                                         errorhandler, "native")
    return result, length

def str_decode_utf_32_be(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(s, size, errors, final,
                                                         errorhandler, "big")
    return result, length

def str_decode_utf_32_le(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(s, size, errors, final,
                                                         errorhandler, "little")
    return result, length

BOM32_DIRECT  = intmask(0x0000FEFF)
BOM32_REVERSE = intmask(0xFFFE0000)

def str_decode_utf_32_helper(s, size, errors, final=True,
                             errorhandler=None,
                             byteorder="native"):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    bo = 0

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
            bom = ((ord(s[iorder[3]]) << 24) | (ord(s[iorder[2]]) << 16) |
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

    result = UnicodeBuilder(size // 4)

    while pos < size:
        # remaining bytes at the end? (size should be divisible by 4)
        if len(s) - pos < 4:
            if not final:
                break
            r, pos = errorhandler(errors, 'utf-32', "truncated data",
                                  s, pos, len(s))
            result.append(r)
            if len(s) - pos < 4:
                break
            continue
        ch = ((ord(s[pos + iorder[3]]) << 24) | (ord(s[pos + iorder[2]]) << 16) |
              (ord(s[pos + iorder[1]]) << 8)  | ord(s[pos + iorder[0]]))
        if ch >= 0x110000:
            r, pos = errorhandler(errors, 'utf-32', "codepoint not in range(0x110000)",
                                  s, pos, len(s))
            result.append(r)
            continue

        if MAXUNICODE < 65536 and ch >= 0x10000:
            ch -= 0x10000L
            result.append(unichr(0xD800 + (ch >> 10)))
            result.append(unichr(0xDC00 + (ch & 0x03FF)))
        else:
            result.append(UNICHR(ch))
        pos += 4
    return result.build(), pos, bo

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

def unicode_encode_utf_32_helper(s, size, errors,
                                 errorhandler=None,
                                 byteorder='little'):
    if size == 0:
        return ""

    result = StringBuilder(size * 4 + 4)
    if byteorder == 'native':
        _STORECHAR32(result, 0xFEFF, BYTEORDER)
        byteorder = BYTEORDER

    i = 0
    while i < size:
        ch = ord(s[i])
        i += 1
        ch2 = 0
        if MAXUNICODE < 65536 and 0xD800 <= ch <= 0xDBFF and i < size:
            ch2 = ord(s[i])
            if 0xDC00 <= ch2 <= 0xDFFF:
                ch = (((ch & 0x3FF)<<10) | (ch2 & 0x3FF)) + 0x10000;
                i += 1
        _STORECHAR32(result, ch, byteorder)

    return result.build()

def unicode_encode_utf_32(s, size, errors,
                          errorhandler=None):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler, "native")


def unicode_encode_utf_32_be(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler, "big")


def unicode_encode_utf_32_le(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler, "little")


# ____________________________________________________________
# utf-7

## indicate whether a UTF-7 character is special i.e. cannot be directly
##       encoded:
##         0 - not special
##         1 - special
##         2 - whitespace (optional)
##         3 - RFC2152 Set O (optional)

_utf7_special = [
    1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 2, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    2, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 1, 0, 0, 0, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 0,
    3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 1, 3, 3, 3,
    3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 1, 1,
]

def _utf7_SPECIAL(oc, encodeO=False, encodeWS=False):
    return (oc > 127 or _utf7_special[oc] == 1 or
            (encodeWS and _utf7_special[oc] == 2) or
            (encodeO and _utf7_special[oc] == 3))

def _utf7_B64CHAR(oc):
    if oc > 127:
        return False
    c = chr(oc)
    return c.isalnum() or c == '+' or c == '/'
def _utf7_TO_BASE64(n):
    "Returns the base-64 character of the bottom 6 bits of n"
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[n & 0x3f]
def _utf7_FROM_BASE64(c):
    "Retuns the base-64 value of a base-64 character"
    if c == '+':
        return 62
    elif c == '/':
        return 63
    elif c >= 'a':
        return ord(c) - 71
    elif c >= 'A':
        return ord(c) - 65
    else:
        return ord(c) + 4

def _utf7_ENCODE(result, ch, bits):
    while bits >= 6:
        result.append(_utf7_TO_BASE64(ch >> (bits - 6)))
        bits -= 6
    return bits

def _utf7_DECODE(s, result, errorhandler, errors,
                 pos, charsleft, bitsleft, surrogate):
    while bitsleft >= 16:
        outCh =  (charsleft >> (bitsleft-16)) & 0xffff
        bitsleft -= 16

        if surrogate:
            ## We have already generated an error for the high
            ## surrogate so let's not bother seeing if the low
            ## surrogate is correct or not
            surrogate = False
        elif 0xDC00 <= outCh <= 0xDFFF:
            ## This is a surrogate pair. Unfortunately we can't
            ## represent it in a 16-bit character
            surrogate = True
            msg = "code pairs are not supported"
            res, pos = errorhandler(errors, 'utf-7',
                                    msg, s, pos-1, pos)
            result.append(res)
            bitsleft = 0
            break
        else:
            result.append(unichr(outCh))
    return pos, charsleft, bitsleft, surrogate


def str_decode_utf_7(s, size, errors, final=False,
                     errorhandler=None):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    if size == 0:
        return u'', 0

    inShift = False
    bitsleft = 0
    startinpos = 0
    charsleft = 0
    surrogate = False

    result = UnicodeBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]
        oc = ord(ch)

        if inShift:
            if ch == '-' or not _utf7_B64CHAR(oc):
                inShift = 0
                pos += 1

                pos, charsleft, bitsleft, surrogate = _utf7_DECODE(
                    s, result, errorhandler, errors,
                    pos, charsleft, bitsleft, surrogate)
                if bitsleft >= 6:
                    ## The shift sequence has a partial character in it. If
                    ## bitsleft < 6 then we could just classify it as padding
                    ## but that is not the case here
                    msg = "partial character in shift sequence"
                    res, pos = errorhandler(errors, 'utf-7',
                                            msg, s, pos-1, pos)
                    result.append(res)
                    ## According to RFC2152 the remaining bits should be
                    ## zero. We choose to signal an error/insert a replacement
                    ## character here so indicate the potential of a
                    ## misencoded character.
                if ch == '-':
                    if pos < size and s[pos] == '-':
                        result.append(u'-')
                        inShift = True

                elif _utf7_SPECIAL(oc):
                    msg = "unexpected special character"
                    res, pos = errorhandler(errors, 'utf-7',
                                            msg, s, pos-1, pos)
                    result.append(res)
                else:
                    result.append(unichr(ord(ch)))
            else:
                charsleft = (charsleft << 6) | _utf7_FROM_BASE64(ch)
                bitsleft += 6
                pos += 1

                pos, charsleft, bitsleft, surrogate = _utf7_DECODE(
                    s, result, errorhandler, errors,
                    pos, charsleft, bitsleft, surrogate)
        elif ch == '+':
            startinpos = pos
            pos += 1
            if pos < size and s[pos] == '-':
                pos += 1
                result.append(u'+')
            else:
                inShift = 1
                bitsleft = 0

        elif _utf7_SPECIAL(oc):
            pos += 1
            msg = "unexpected special character"
            res, pos = errorhandler(errors, 'utf-7', msg, s, pos-1, pos)
            result.append(res)
        else:
            result.append(unichr(oc))
            pos += 1

    if inShift and final:
        endinpos = size
        msg = "unterminated shift sequence"
        res, pos = errorhandler(errors, 'utf-7', msg, s, startinpos, pos)
        result.append(res)

    return result.build(), pos

def unicode_encode_utf_7(s, size, errors, errorhandler=None):
    if size == 0:
        return ''
    result = StringBuilder(size)

    encodeSetO = encodeWhiteSpace = False

    inShift = False
    bitsleft = 0
    charsleft = 0

    pos = 0
    while pos < size:
        ch = s[pos]
        oc = ord(ch)
        if not inShift:
            if ch == u'+':
                result.append('+-')
            elif _utf7_SPECIAL(oc, encodeSetO, encodeWhiteSpace):
                charsleft = oc
                bitsleft = 16
                result.append('+')
                bitsleft = _utf7_ENCODE(result, charsleft, bitsleft)
                inShift = bitsleft > 0
            else:
                result.append(chr(oc))
        else:
            if not _utf7_SPECIAL(oc, encodeSetO, encodeWhiteSpace):
                result.append(_utf7_TO_BASE64(charsleft << (6-bitsleft)))
                charsleft = 0
                bitsleft = 0
                ## Characters not in the BASE64 set implicitly unshift the
                ## sequence so no '-' is required, except if the character is
                ## itself a '-'
                if _utf7_B64CHAR(oc) or ch == u'-':
                    result.append('-')
                inShift = False
                result.append(chr(oc))
            else:
                bitsleft += 16
                charsleft = (charsleft << 16) | oc
                bitsleft =  _utf7_ENCODE(result, charsleft, bitsleft)
                ## If the next character is special then we dont' need to
                ## terminate the shift sequence. If the next character is not
                ## a BASE64 character or '-' then the shift sequence will be
                ## terminated implicitly and we don't have to insert a '-'.
                if bitsleft == 0:
                    if pos + 1 < size:
                        ch2 = s[pos + 1]
                        oc2 = ord(ch2)

                        if _utf7_SPECIAL(oc2, encodeSetO, encodeWhiteSpace):
                            pass
                        elif _utf7_B64CHAR(oc2) or ch2 == u'-':
                            result.append('-')
                            inShift = False
                        else:
                            inShift = False
                    else:
                        result.append('-')
                        inShift = False
        pos += 1

    if bitsleft:
        result.append(_utf7_TO_BASE64(charsleft << (6 - bitsleft)))
        result.append('-')

    return result.build()

# ____________________________________________________________
# ascii and latin-1

def str_decode_latin_1(s, size, errors, final=False,
                       errorhandler=None):
    # latin1 is equivalent to the first 256 ordinals in Unicode.
    pos = 0
    result = UnicodeBuilder(size)
    while pos < size:
        result.append(unichr(ord(s[pos])))
        pos += 1
    return result.build(), pos


def str_decode_ascii(s, size, errors, final=False,
                     errorhandler=None):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    # ASCII is equivalent to the first 128 ordinals in Unicode.
    result = UnicodeBuilder(size)
    pos = 0
    while pos < size:
        c = s[pos]
        if ord(c) < 128:
            result.append(unichr(ord(c)))
            pos += 1
        else:
            r, pos = errorhandler(errors, "ascii", "ordinal not in range(128)",
                                  s,  pos, pos + 1)
            result.append(r)
    return result.build(), pos


def unicode_encode_ucs1_helper(p, size, errors,
                               errorhandler=None, limit=256):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_encode
    if limit == 256:
        reason = "ordinal not in range(256)"
        encoding = "latin-1"
    else:
        reason = "ordinal not in range(128)"
        encoding = "ascii"

    if size == 0:
        return ''
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        ch = p[pos]
        
        if ord(ch) < limit:
            result.append(chr(ord(ch)))
            pos += 1
        else:
            # startpos for collecting unencodable chars
            collstart = pos 
            collend = pos+1 
            while collend < len(p) and ord(p[collend]) >= limit:
                collend += 1
            r, pos = errorhandler(errors, encoding, reason, p,
                                  collstart, collend)
            result.append(r)
    
    return result.build()

def unicode_encode_latin_1(p, size, errors, errorhandler=None):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 256)
    return res

def unicode_encode_ascii(p, size, errors, errorhandler=None):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 128)
    return res

# ____________________________________________________________
# Charmap

ERROR_CHAR = u'\ufffe'

@specialize.argtype(5)
def str_decode_charmap(s, size, errors, final=False,
                       errorhandler=None, mapping=None):
    "mapping can be a rpython dictionary, or a dict-like object."

    # Default to Latin-1
    if mapping is None:
        return str_decode_latin_1(s, size, errors, final=final,
                                  errorhandler=errorhandler)
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    if size == 0:
        return u'', 0

    pos = 0
    result = UnicodeBuilder(size)
    while pos < size:
        ch = s[pos]

        c = mapping.get(ch, ERROR_CHAR)
        if c == ERROR_CHAR:
            r, pos = errorhandler(errors, "charmap",
                                  "character maps to <undefined>",
                                  s,  pos, pos + 1)
            result.append(r)
            continue
        result.append(c)
        pos += 1
    return result.build(), pos

def unicode_encode_charmap(s, size, errors, errorhandler=None,
                           mapping=None):
    if mapping is None:
        return unicode_encode_latin_1(s, size, errors,
                                      errorhandler=errorhandler)

    if errorhandler is None:
        errorhandler = raise_unicode_exception_encode

    if size == 0:
        return ''
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        c = mapping.get(ch, '')
        if len(c) == 0:
            res, pos = errorhandler(errors, "charmap",
                                    "character maps to <undefined>",
                                    s, pos, pos + 1)
            for ch2 in res:
                c2 = mapping.get(unichr(ord(ch2)), '')
                if len(c2) == 0:
                    errorhandler(
                        "strict", "charmap",
                        "character maps to <undefined>",
                        s,  pos, pos + 1)
                result.append(c2)
            continue
        result.append(c)
        pos += 1
    return result.build()

# ____________________________________________________________
# Unicode escape

hexdigits = "0123456789ABCDEFabcdef"

def hexescape(builder, s, pos, digits,
              encoding, errorhandler, message, errors):
    import sys
    chr = 0
    if pos + digits > len(s):
        message = "end of string in escape sequence"
        res, pos = errorhandler(errors, "unicodeescape",
                                message, s, pos-2, len(s))
        builder.append(res)
    else:
        try:
            chr = r_uint(int(s[pos:pos+digits], 16))
        except ValueError:
            endinpos = pos
            while s[endinpos] in hexdigits:
                endinpos += 1
            res, pos = errorhandler(errors, encoding,
                                    message, s, pos-2, endinpos+1)
            builder.append(res)
        else:
            # when we get here, chr is a 32-bit unicode character
            if chr <= MAXUNICODE:
                builder.append(UNICHR(chr))
                pos += digits

            elif chr <= 0x10ffff:
                chr -= 0x10000L
                builder.append(unichr(0xD800 + (chr >> 10)))
                builder.append(unichr(0xDC00 + (chr & 0x03FF)))
                pos += digits
            else:
                message = "illegal Unicode character"
                res, pos = errorhandler(errors, encoding,
                                        message, s, pos-2, pos+digits)
                builder.append(res)
    return pos

def str_decode_unicode_escape(s, size, errors, final=False,
                              errorhandler=False,
                              unicodedata_handler=None):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode

    if size == 0:
        return u'', 0

    builder = UnicodeBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            builder.append(unichr(ord(ch)))
            pos += 1
            continue

        # - Escapes
        pos += 1
        if pos >= size:
            message = "\\ at end of string"
            res, pos = errorhandler(errors, "unicodeescape",
                                    message, s, pos-1, size)
            builder.append(res)
            continue

        ch = s[pos]
        pos += 1
        # \x escapes
        if ch == '\n': pass
        elif ch == '\\': builder.append(u'\\')
        elif ch == '\'': builder.append(u'\'')
        elif ch == '\"': builder.append(u'\"')
        elif ch == 'b' : builder.append(u'\b')
        elif ch == 'f' : builder.append(u'\f')
        elif ch == 't' : builder.append(u'\t')
        elif ch == 'n' : builder.append(u'\n')
        elif ch == 'r' : builder.append(u'\r')
        elif ch == 'v' : builder.append(u'\v')
        elif ch == 'a' : builder.append(u'\a')
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
            builder.append(unichr(x))
        # hex escapes
        # \xXX
        elif ch == 'x':
            digits = 2
            message = "truncated \\xXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        # \uXXXX
        elif ch == 'u':
            digits = 4
            message = "truncated \\uXXXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        #  \UXXXXXXXX
        elif ch == 'U':
            digits = 8
            message = "truncated \\UXXXXXXXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        # \N{name}
        elif ch == 'N':
            message = "malformed \\N character escape"
            look = pos
            if unicodedata_handler is None:
                message = ("\\N escapes not supported "
                           "(can't load unicodedata module)")
                res, pos = errorhandler(errors, "unicodeescape",
                                        message, s, pos-1, size)
                builder.append(res)
                continue

            if look < size and s[look] == '{':
                # look for the closing brace
                while look < size and s[look] != '}':
                    look += 1
                if look < size and s[look] == '}':
                    # found a name.  look it up in the unicode database
                    message = "unknown Unicode character name"
                    name = s[pos+1:look]
                    code = unicodedata_handler.call(name)
                    if code < 0:
                        res, pos = errorhandler(errors, "unicodeescape",
                                                message, s, pos-1, look+1)
                        builder.append(res)
                        continue
                    pos = look + 1
                    if code <= MAXUNICODE:
                        builder.append(UNICHR(code))
                    else:
                        code -= 0x10000L
                        builder.append(unichr(0xD800 + (code >> 10)))
                        builder.append(unichr(0xDC00 + (code & 0x03FF)))
                else:
                    res, pos = errorhandler(errors, "unicodeescape",
                                            message, s, pos-1, look+1)
                    builder.append(res)
            else:
                res, pos = errorhandler(errors, "unicodeescape",
                                        message, s, pos-1, look+1)
                builder.append(res)
        else:
            builder.append(u'\\')
            builder.append(unichr(ord(ch)))

    return builder.build(), pos

def unicode_encode_unicode_escape(s, size, errors, errorhandler=None, quotes=False):
    # errorhandler is not used: this function cannot cause Unicode errors
    result = StringBuilder(size)

    if quotes:
        if s.find(u'\'') != -1 and s.find(u'\"') == -1:
            quote = ord('\"')
            result.append('u"')
        else:
            quote = ord('\'')
            result.append('u\'')
    else:
        quote = 0

        if size == 0:
            return ''

    pos = 0
    while pos < size:
        ch = s[pos]
        oc = ord(ch)

        # Escape quotes
        if quotes and (oc == quote or ch == '\\'):
            result.append('\\')
            result.append(chr(oc))
            pos += 1
            continue

        if 0xD800 <= oc < 0xDC00 and pos + 1 < size:
            # Map UTF-16 surrogate pairs to Unicode \UXXXXXXXX escapes
            pos += 1
            oc2 = ord(s[pos])

            if 0xDC00 <= oc2 <= 0xDFFF:
                ucs = (((oc & 0x03FF) << 10) | (oc2 & 0x03FF)) + 0x00010000
                raw_unicode_escape_helper(result, ucs)
                pos += 1
                continue
            # Fall through: isolated surrogates are copied as-is
            pos -= 1

        # Map special whitespace to '\t', \n', '\r'
        if ch == '\t':
            result.append('\\t')
        elif ch == '\n':
            result.append('\\n')
        elif ch == '\r':
            result.append('\\r')
        elif ch == '\\':
            result.append('\\\\')

        # Map non-printable or non-ascii to '\xhh' or '\uhhhh'
        elif oc < 32 or oc >= 0x7F:
            raw_unicode_escape_helper(result, oc)

        # Copy everything else as-is
        else:
            result.append(chr(oc))
        pos += 1

    if quotes:
        result.append(chr(quote))
    return result.build()

# ____________________________________________________________
# Raw unicode escape

def str_decode_raw_unicode_escape(s, size, errors, final=False,
                                  errorhandler=None):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    if size == 0:
        return u'', 0

    result = UnicodeBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            result.append(unichr(ord(ch)))
            pos += 1
            continue

        startinpos = pos
        # \u-escapes are only interpreted iff the number of leading
        # backslashes is odd
        bs = pos
        while pos < size:
            pos += 1
            if pos == size or s[pos] != '\\':
                break
            result.append(u'\\')

        # we have a backslash at the end of the string, stop here
        if pos >= size:
            result.append(u'\\')
            break

        if ((pos - bs) & 1 == 0 or
            pos >= size or
            (s[pos] != 'u' and s[pos] != 'U')):
            result.append(u'\\')
            result.append(unichr(ord(s[pos])))
            pos += 1
            continue

        if s[pos] == 'u':
            digits = 4
            message = "truncated \\uXXXX escape"
        else:
            digits = 8
            message = "truncated \\UXXXXXXXX escape"
        pos += 1
        pos = hexescape(result, s, pos, digits,
                        "rawunicodeescape", errorhandler, message, errors)

    return result.build(), pos

def raw_unicode_escape_helper(result, char):
    num = hex(char)
    if char >= 0x10000:
        result.append("\\U")
        zeros = 8
    elif char >= 0x100:
        result.append("\\u")
        zeros = 4
    else:
        result.append("\\x")
        zeros = 2
    lnum = len(num)
    nb = zeros + 2 - lnum # num starts with '0x'
    if nb > 0:
        result.append_multiple_char('0', nb)
    result.append_slice(num, 2, lnum)

def unicode_encode_raw_unicode_escape(s, size, errors, errorhandler=None):
    # errorhandler is not used: this function cannot cause Unicode errors
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
# unicode-internal

def str_decode_unicode_internal(s, size, errors, final=False,
                                errorhandler=None):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    if size == 0:
        return u'', 0

    if MAXUNICODE < 65536:
        unicode_bytes = 2
    else:
        unicode_bytes = 4
    if BYTEORDER == "little":
        start = 0
        stop = unicode_bytes
        step = 1
    else:
        start = unicode_bytes - 1
        stop = -1
        step = -1

    result = UnicodeBuilder(size // unicode_bytes)
    pos = 0
    while pos < size:
        if pos > size - unicode_bytes:
            res, pos = errorhandler(errors, "unicode_internal",
                                    "truncated input",
                                    s, pos, size)
            result.append(res)
            if pos > size - unicode_bytes:
                break
            continue
        t = r_uint(0)
        h = 0
        for j in range(start, stop, step):
            t += r_uint(ord(s[pos + j])) << (h*8)
            h += 1
        if t > MAXUNICODE:
            res, pos = errorhandler(errors, "unicode_internal",
                                    "unichr(%d) not in range" % (t,),
                                    s, pos, pos + unicode_bytes)
            result.append(res)
            continue
        result.append(unichr(t))
        pos += unicode_bytes
    return result.build(), pos

def unicode_encode_unicode_internal(s, size, errors, errorhandler=None):
    if size == 0:
        return ''

    if MAXUNICODE < 65536:
        unicode_bytes = 2
    else:
        unicode_bytes = 4

    result = StringBuilder(size * unicode_bytes)
    pos = 0
    while pos < size:
        oc = ord(s[pos])
        if MAXUNICODE < 65536:
            if BYTEORDER == "little":
                result.append(chr(oc       & 0xFF))
                result.append(chr(oc >>  8 & 0xFF))
            else:
                result.append(chr(oc >>  8 & 0xFF))
                result.append(chr(oc       & 0xFF))
        else:
            if BYTEORDER == "little":
                result.append(chr(oc       & 0xFF))
                result.append(chr(oc >>  8 & 0xFF))
                result.append(chr(oc >> 16 & 0xFF))
                result.append(chr(oc >> 24 & 0xFF))
            else:
                result.append(chr(oc >> 24 & 0xFF))
                result.append(chr(oc >> 16 & 0xFF))
                result.append(chr(oc >>  8 & 0xFF))
                result.append(chr(oc       & 0xFF))
        pos += 1

    return result.build()

# ____________________________________________________________
# MBCS codecs for Windows

if sys.platform == 'win32':
    from pypy.rpython.lltypesystem import lltype, rffi
    from pypy.rlib import rwin32
    CP_ACP = 0

    MultiByteToWideChar = rffi.llexternal('MultiByteToWideChar',
                                          [rffi.UINT, rwin32.DWORD,
                                           rwin32.LPCSTR, rffi.INT,
                                           rffi.CWCHARP, rffi.INT],
                                          rffi.INT,
                                          calling_conv='win')

    WideCharToMultiByte = rffi.llexternal('WideCharToMultiByte',
                                          [rffi.UINT, rwin32.DWORD,
                                           rffi.CWCHARP, rffi.INT,
                                           rwin32.LPCSTR, rffi.INT,
                                           rwin32.LPCSTR, rffi.VOIDP],
                                          rffi.INT,
                                          calling_conv='win')

    def is_dbcs_lead_byte(c):
        # XXX don't know how to test this
        return False

    def str_decode_mbcs(s, size, errors, final=False,
                        errorhandler=None):
        if size == 0:
            return u"", 0

        if errorhandler is None:
            errorhandler = raise_unicode_exception_decode

        # Skip trailing lead-byte unless 'final' is set
        if not final and is_dbcs_lead_byte(s[size-1]):
            size -= 1

        dataptr = rffi.get_nonmovingbuffer(s)
        try:
            # first get the size of the result
            usize = MultiByteToWideChar(CP_ACP, 0,
                                        dataptr, size,
                                        lltype.nullptr(rffi.CWCHARP.TO), 0)
            if usize == 0:
                raise rwin32.lastWindowsError()

            raw_buf, gc_buf = rffi.alloc_unicodebuffer(usize)
            try:
                # do the conversion
                if MultiByteToWideChar(CP_ACP, 0,
                                       dataptr, size, raw_buf, usize) == 0:
                    raise rwin32.lastWindowsError()

                return (rffi.unicode_from_buffer(raw_buf, gc_buf, usize, usize),
                        size)
            finally:
                rffi.keep_unicodebuffer_alive_until_here(raw_buf, gc_buf)
        finally:
            rffi.free_nonmovingbuffer(s, dataptr)

    def unicode_encode_mbcs(p, size, errors, errorhandler=None):
        dataptr = rffi.get_nonmoving_unicodebuffer(p)
        try:
            # first get the size of the result
            if size > 0:
                mbcssize = WideCharToMultiByte(CP_ACP, 0,
                                               dataptr, size, None, 0,
                                               None, None)
                if mbcssize == 0:
                    raise rwin32.lastWindowsError()
            else:
                mbcssize = 0

            raw_buf, gc_buf = rffi.alloc_buffer(mbcssize)
            try:
                # do the conversion
                if WideCharToMultiByte(CP_ACP, 0,
                                       dataptr, size, raw_buf, mbcssize,
                                       None, None) == 0:
                    raise rwin32.lastWindowsError()

                return rffi.str_from_buffer(raw_buf, gc_buf, mbcssize, mbcssize)
            finally:
                rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        finally:
            rffi.free_nonmoving_unicodebuffer(p, dataptr)
