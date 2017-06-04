from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_uint, r_ulonglong, intmask
from rpython.rtyper.lltypesystem import lltype, rffi

SIZE_UNICODE = rffi.sizeof(lltype.UniChar)


if SIZE_UNICODE == 4:
    def ordinal_to_unicode(ordinal):    # 'ordinal' is a r_uint
        return unichr(intmask(ordinal))
else:
    def ordinal_to_unicode(ordinal):    # 'ordinal' is a r_uint
        if ordinal <= 0xffff:
            return unichr(intmask(ordinal))
        else:
            ordinal = intmask(ordinal - 0x10000)
            return (unichr(0xD800 | (ordinal >> 10)) +
                    unichr(0xDC00 | (ordinal & 0x3FF)))

def is_surrogate(u, index):
    return (index + 1 < len(u) and
            unichr(0xD800) <= u[index + 0] <= unichr(0xDBFF) and
            unichr(0xDC00) <= u[index + 1] <= unichr(0xDFFF))

def as_surrogate(u, index):
    ordinal = (ord(u[index + 0]) - 0xD800) << 10
    ordinal |= (ord(u[index + 1]) - 0xDC00)
    return r_uint(ordinal + 0x10000)

def unicode_to_ordinal(u):
    if len(u) == 1:
        u = ord(u[0])
        return r_uint(u)
    elif SIZE_UNICODE == 2:
        if len(u) == 2 and is_surrogate(u, 0):
            return r_uint(as_surrogate(u, 0))
    raise ValueError


class OutOfRange(Exception):
    def __init__(self, ordinal):
        ordinal = intmask(rffi.cast(rffi.INT, ordinal))
        self.ordinal = ordinal


if SIZE_UNICODE == 2:
    def unicode_from_char32(ptr, length):
        ptr = rffi.cast(rffi.UINTP, ptr)
        alloc = length
        for i in range(length):
            if rffi.cast(lltype.Unsigned, ptr[i]) > 0xFFFF:
                alloc += 1

        u = [u'\x00'] * alloc
        j = 0
        for i in range(length):
            ordinal = rffi.cast(lltype.Unsigned, ptr[i])
            if ordinal > 0xFFFF:
                if ordinal > 0x10FFFF:
                    raise OutOfRange(ordinal)
                ordinal = intmask(ordinal - 0x10000)
                u[j] = unichr(0xD800 | (ordinal >> 10))
                j += 1
                u[j] = unichr(0xDC00 | (ordinal & 0x3FF))
                j += 1
            else:
                u[j] = unichr(intmask(ordinal))
                j += 1
        assert j == len(u)
        return u''.join(u)

    def unicode_from_char16(ptr, length):
        return rffi.wcharpsize2unicode(rffi.cast(rffi.CWCHARP, ptr), length)

else:
    def unicode_from_char32(ptr, length):
        return rffi.wcharpsize2unicode(rffi.cast(rffi.CWCHARP, ptr), length)

    def unicode_from_char16(ptr, length):
        ptr = rffi.cast(rffi.USHORTP, ptr)
        u = [u'\x00'] * length
        i = 0
        j = 0
        while j < length:
            ch = intmask(ptr[j])
            j += 1
            if 0xD800 <= ch <= 0xDBFF and j < length:
                ch2 = intmask(ptr[j])
                if 0xDC00 <= ch2 <= 0xDFFF:
                    ch = (((ch & 0x3FF)<<10) | (ch2 & 0x3FF)) + 0x10000
                    j += 1
            u[i] = unichr(ch)
            i += 1
        del u[i:]
        return u''.join(u)


@specialize.ll()
def _measure_length(ptr, maxlen):
    result = 0
    if maxlen < 0:
        while intmask(ptr[result]) != 0:
            result += 1
    else:
        while result < maxlen and intmask(ptr[result]) != 0:
            result += 1
    return result

def measure_length_16(ptr, maxlen=-1):
    return _measure_length(rffi.cast(rffi.USHORTP, ptr), maxlen)

def measure_length_32(ptr, maxlen=-1):
    return _measure_length(rffi.cast(rffi.UINTP, ptr), maxlen)


def unicode_to_char16(u, ptr):
    XXX
