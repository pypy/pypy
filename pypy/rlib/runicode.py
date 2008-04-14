import sys
from pypy.lang.smalltalk.tool.bitmanipulation import splitter

MAXUNICODE = sys.maxunicode
BYTEORDER = sys.byteorder


def raise_unicode_exception_decode(errors, encoding, msg, s,
                                   startingpos, endingpos):
    assert isinstance(s, str)
    raise UnicodeDecodeError(
            encoding, s[startingpos], startingpos, endingpos, msg)

def raise_unicode_exception_encode(errors, encoding, msg, u,
                                   startingpos, endingpos):
    assert isinstance(u, unicode)
    raise UnicodeEncodeError(
            encoding, u[startingpos], startingpos, endingpos, msg)

# ____________________________________________________________ 
# unicode decoding

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
    if (size == 0):
        return u'', 0
    result = []
    pos = 0
    while pos < size:
        ch = s[pos]
        ordch1 = ord(ch)
        if ordch1 < 0x80:
            result.append(unichr(ordch1))
            pos += 1
            continue

        n = utf8_code_length[ordch1]
        if (pos + n > size):
            if not final:
                break
            else:
                r, pos = errorhandler(errors, "utf-8",
                                      "unexpected end of data", s,  pos, size)
                result.append(r)
                if (pos + n > size):
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
            if (two != 2):
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
            if (two1 != 2 or two2 != 2):
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
            if (two1 != 2 or two2 != 2 or two3 != 2):
                r, pos = errorhandler(errors, "utf-8", "invalid data",
                                      s,  pos, pos + 4)
                result.append(r)
            else:
                c = (w << 18) + (x << 12) + (y << 6) + z
                # minimum value allowed for 4 byte encoding
                # maximum value allowed for UTF-16
                if ((c < 0x10000) or (c > 0x10ffff)):
                    r, pos = errorhandler(errors, "utf-8", "illegal encoding",
                                          s,  pos, pos + 4)
                    result.append(r)
                else:
                    # convert to UTF-16 if necessary
                    if c < MAXUNICODE:
                        result.append(unichr(c))
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

    return u"".join(result), pos


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
    consumed = 0

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
    result = []
    if byteorder == 'native':
        if (size >= 2):
            bom = (ord(s[ihi]) << 8) | ord(s[ilo])
            if BYTEORDER == 'little':
                if (bom == 0xFEFF):
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
    if (size == 0):
        return u'', 0, bo
    if (bo == -1):
        # force little endian
        ihi = 1
        ilo = 0

    elif (bo == 1):
        # force big endian
        ihi = 0
        ilo = 1

    #XXX I think the errors are not correctly handled here
    while (pos < len(s)):
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
        if (ch < 0xD800 or ch > 0xDFFF):
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
        elif (0xD800 <= ch and ch <= 0xDBFF):
            ch2 = (ord(s[pos+ihi]) << 8) | ord(s[pos+ilo])
            pos += 2
            if (0xDC00 <= ch2 and ch2 <= 0xDFFF):
                if MAXUNICODE < 65536:
                    result.append(unichr(ch))
                    result.append(unichr(ch2))
                else:
                    result.append(unichr((((ch & 0x3FF)<<10) |
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
    return u"".join(result), pos, bo

def str_decode_latin_1(s, size, errors, final=False,
                       errorhandler=None):
    # latin1 is equivalent to the first 256 ordinals in Unicode.
    pos = 0
    result = []
    while (pos < size):
        result.append(unichr(ord(s[pos])))
        pos += 1
    return u"".join(result), pos


def str_decode_ascii(s, size, errors, final=False,
                     errorhandler=None):
    if errorhandler is None:
        errorhandler = raise_unicode_exception_decode
    # ASCII is equivalent to the first 128 ordinals in Unicode.
    result = []
    pos = 0
    while pos < len(s):
        c = s[pos]
        if ord(c) < 128:
            result.append(unichr(ord(c)))
            pos += 1
        else:
            r, pos = errorhandler(errors, "ascii", "ordinal not in range(128)",
                                  s,  pos, pos + 1)
            result.append(r)
    return u"".join(result), pos


# ____________________________________________________________ 
# unicode encoding 


def unicode_encode_utf_8(s, size, errors, errorhandler=None):
    assert(size >= 0)
    result = []
    i = 0
    while i < size:
        ch = ord(s[i])
        i += 1
        if (ch < 0x80):
            # Encode ASCII 
            result.append(chr(ch))
        elif (ch < 0x0800) :
            # Encode Latin-1 
            result.append(chr((0xc0 | (ch >> 6))))
            result.append(chr((0x80 | (ch & 0x3f))))
        else:
            # Encode UCS2 Unicode ordinals
            if (ch < 0x10000):
                # Special case: check for high surrogate
                if (0xD800 <= ch and ch <= 0xDBFF and i != size) :
                    ch2 = ord(s[i])
                    # Check for low surrogate and combine the two to
                    # form a UCS4 value
                    if (0xDC00 <= ch2 and ch2 <= 0xDFFF) :
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
    return "".join(result)

def _encodeUCS4(result, ch):
    # Encode UCS4 Unicode ordinals
    result.append((chr((0xf0 | (ch >> 18)))))
    result.append((chr((0x80 | ((ch >> 12) & 0x3f)))))
    result.append((chr((0x80 | ((ch >> 6) & 0x3f)))))
    result.append((chr((0x80 | (ch & 0x3f)))))


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
    
    if (size == 0):
        return ''
    result = []
    pos = 0
    while pos < len(p):
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
            result += r   # extend 'result' as a list of characters
    
    return "".join(result)

def unicode_encode_latin_1(p, size, errors, errorhandler=None):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 256)
    return res

def unicode_encode_ascii(p, size, errors, errorhandler=None):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 128)
    return res


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
    result = []
    if (byteorder == 'native'):
        _STORECHAR(result, 0xFEFF, BYTEORDER)
        byteorder = BYTEORDER
        
    if size == 0:
        return ""

    i = 0
    while i < size:
        ch = ord(s[i])
        i += 1
        ch2 = 0
        if (ch >= 0x10000) :
            ch2 = 0xDC00 | ((ch-0x10000) & 0x3FF)
            ch  = 0xD800 | ((ch-0x10000) >> 10)

        _STORECHAR(result, ch, byteorder)
        if ch2:
            _STORECHAR(result, ch2, byteorder)

    return "".join(result)

def unicode_encode_utf_16(s, size, errors,
                          errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "native")


def unicode_encode_utf_16_be(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "big")


def unicode_encode_utf_16_le(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "little")
