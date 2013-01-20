
import sys
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import we_are_translated


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

if MAXUNICODE > 0xFFFF:
    def code_to_unichr(code):
        if not we_are_translated() and sys.maxunicode == 0xFFFF:
            # Host CPython is narrow build, generate surrogates
            return UNICHR(code)
        else:
            return unichr(code)
else:
    def code_to_unichr(code):
        # generate surrogates for large codes
        return UNICHR(code)    


def UNICHR(c):
    if c <= sys.maxunicode and c <= MAXUNICODE:
        return unichr(c)
    else:
        c -= 0x10000
        return (unichr(0xD800 + (c >> 10)) +
                unichr(0xDC00 + (c & 0x03FF)))

def ORD(u):
    assert isinstance(u, unicode)
    if len(u) == 1:
        return ord(u[0])
    elif len(u) == 2:
        ch1 = ord(u[0])
        ch2 = ord(u[1])
        if 0xD800 <= ch1 <= 0xDBFF and 0xDC00 <= ch2 <= 0xDFFF:
            return (((ch1 - 0xD800) << 10) | (ch2 - 0xDC00)) + 0x10000
    raise ValueError

def _STORECHAR(result, CH, byteorder):
    hi = chr(((CH) >> 8) & 0xff)
    lo = chr((CH) & 0xff)
    if byteorder == 'little':
        result.append(lo)
        result.append(hi)
    else:
        result.append(hi)
        result.append(lo)
