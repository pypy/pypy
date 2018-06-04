from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rstring import StringBuilder, UnicodeBuilder
from rpython.rlib import runicode
from rpython.rlib.runicode import (
    default_unicode_error_encode, default_unicode_error_decode,
    MAXUNICODE, BYTEORDER, BYTEORDER2, UNICHR)
from pypy.interpreter.error import OperationError

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
    def raise_unicode_exception_encode(errors, encoding, msg, u,
                                       startingpos, endingpos):
        raise OperationError(space.w_UnicodeEncodeError,
                             space.newtuple([space.newtext(encoding),
                                             space.newunicode(u),
                                             space.newint(startingpos),
                                             space.newint(endingpos),
                                             space.newtext(msg)]))
    return raise_unicode_exception_encode

# ____________________________________________________________

def encode(space, w_data, encoding=None, errors='strict'):
    from pypy.objspace.std.unicodeobject import encode_object
    return encode_object(space, w_data, encoding, errors)

# These functions take and return unwrapped rpython strings and unicodes
def decode_unicode_escape(space, string):
    from pypy.module._codecs import interp_codecs
    state = space.fromcache(interp_codecs.CodecState)
    unicodedata_handler = state.get_unicodedata_handler(space)
    result, consumed = runicode.str_decode_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        unicodedata_handler=unicodedata_handler)
    return result

def decode_raw_unicode_escape(space, string):
    result, consumed = runicode.str_decode_raw_unicode_escape(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space))
    return result

def decode_utf8(space, string):
    # Surrogates are accepted and not treated specially at all.
    # If there happen to be two 3-bytes encoding a pair of surrogates,
    # you still get two surrogate unicode characters in the result.
    # These are the Python2 rules; Python3 differs.
    result, consumed = runicode.str_decode_utf_8(
        string, len(string), "strict",
        final=True, errorhandler=decode_error_handler(space),
        allow_surrogates=True)
    return result

def encode_utf8(space, uni):
    # Note that this function never raises UnicodeEncodeError,
    # since surrogates are allowed, either paired or lone.
    # A paired surrogate is considered like the non-BMP character
    # it stands for.  These are the Python2 rules; Python3 differs.
    return runicode.unicode_encode_utf_8(
        uni, len(uni), "strict",
        errorhandler=None,
        allow_surrogates=True)

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
                             byteorder="native",
                             public_encoding_name='utf16'):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
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
            r, pos = errorhandler(errors, public_encoding_name,
                                  "truncated data",
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
                if MAXUNICODE < 65536:
                    result.append(unichr(ch))
                    result.append(unichr(ch2))
                else:
                    result.append(UNICHR((((ch & 0x3FF)<<10) |
                                           (ch2 & 0x3FF)) + 0x10000))
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
                                 allow_surrogates=True,
                                 byteorder='little',
                                 public_encoding_name='utf16'):
    if errorhandler is None:
        errorhandler = default_unicode_error_encode
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
        ch = ord(s[pos])
        pos += 1

        if ch < 0xD800:
            _STORECHAR(result, ch, byteorder)
        elif ch >= 0x10000:
            _STORECHAR(result, 0xD800 | ((ch-0x10000) >> 10), byteorder)
            _STORECHAR(result, 0xDC00 | ((ch-0x10000) & 0x3FF), byteorder)
        elif ch >= 0xE000 or allow_surrogates:
            _STORECHAR(result, ch, byteorder)
        else:
            ru, rs, pos = errorhandler(errors, public_encoding_name,
                                       'surrogates not allowed',
                                       s, pos-1, pos)
            if rs is not None:
                # py3k only
                if len(rs) % 2 != 0:
                    errorhandler('strict', public_encoding_name,
                                 'surrogates not allowed',
                                 s, pos-1, pos)
                result.append(rs)
                continue
            for ch in ru:
                if ord(ch) < 0xD800:
                    _STORECHAR(result, ord(ch), byteorder)
                else:
                    errorhandler('strict', public_encoding_name,
                                 'surrogates not allowed',
                                 s, pos-1, pos)
            continue

    return result.build()

def unicode_encode_utf_16(s, size, errors,
                          errorhandler=None,
                          allow_surrogates=True):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler,
                                        allow_surrogates, "native")

def unicode_encode_utf_16_be(s, size, errors,
                             errorhandler=None,
                             allow_surrogates=True):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler,
                                        allow_surrogates, "big")

def unicode_encode_utf_16_le(s, size, errors,
                             errorhandler=None,
                             allow_surrogates=True):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler,
                                        allow_surrogates, "little")


# ____________________________________________________________
# utf-32

def str_decode_utf_32(s, size, errors, final=True,
                      errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(
        s, size, errors, final, errorhandler, "native")
    return result, length

def str_decode_utf_32_be(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(
        s, size, errors, final, errorhandler, "big")
    return result, length

def str_decode_utf_32_le(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(
        s, size, errors, final, errorhandler, "little")
    return result, length

BOM32_DIRECT = intmask(0x0000FEFF)
BOM32_REVERSE = intmask(0xFFFE0000)

def str_decode_utf_32_helper(s, size, errors, final=True,
                             errorhandler=None,
                             byteorder="native",
                             public_encoding_name='utf32'):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
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
            bom = intmask(
                (ord(s[iorder[3]]) << 24) | (ord(s[iorder[2]]) << 16) |
                (ord(s[iorder[1]]) << 8) | ord(s[iorder[0]]))
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
            r, pos = errorhandler(errors, public_encoding_name,
                                  "truncated data",
                                  s, pos, len(s))
            result.append(r)
            if len(s) - pos < 4:
                break
            continue
        ch = ((ord(s[pos + iorder[3]]) << 24) | (ord(s[pos + iorder[2]]) << 16) |
            (ord(s[pos + iorder[1]]) << 8) | ord(s[pos + iorder[0]]))
        if ch >= 0x110000:
            r, pos = errorhandler(errors, public_encoding_name,
                                  "codepoint not in range(0x110000)",
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
                                 allow_surrogates=True,
                                 byteorder='little',
                                 public_encoding_name='utf32'):
    if errorhandler is None:
        errorhandler = default_unicode_error_encode
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
        ch = ord(s[pos])
        pos += 1
        ch2 = 0
        if not allow_surrogates and 0xD800 <= ch < 0xE000:
            ru, rs, pos = errorhandler(
                errors, public_encoding_name, 'surrogates not allowed',
                s, pos - 1, pos)
            if rs is not None:
                # py3k only
                if len(rs) % 4 != 0:
                    errorhandler(
                        'strict', public_encoding_name, 'surrogates not allowed',
                        s, pos - 1, pos)
                result.append(rs)
                continue
            for ch in ru:
                if ord(ch) < 0xD800:
                    _STORECHAR32(result, ord(ch), byteorder)
                else:
                    errorhandler(
                        'strict', public_encoding_name,
                        'surrogates not allowed', s, pos - 1, pos)
            continue
        if 0xD800 <= ch < 0xDC00 and MAXUNICODE < 65536 and pos < size:
            ch2 = ord(s[pos])
            if 0xDC00 <= ch2 < 0xE000:
                ch = (((ch & 0x3FF) << 10) | (ch2 & 0x3FF)) + 0x10000
                pos += 1
        _STORECHAR32(result, ch, byteorder)

    return result.build()

def unicode_encode_utf_32(s, size, errors,
                          errorhandler=None, allow_surrogates=True):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler,
                                        allow_surrogates, "native")

def unicode_encode_utf_32_be(s, size, errors,
                             errorhandler=None, allow_surrogates=True):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler,
                                        allow_surrogates, "big")

def unicode_encode_utf_32_le(s, size, errors,
                             errorhandler=None, allow_surrogates=True):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler,
                                        allow_surrogates, "little")
