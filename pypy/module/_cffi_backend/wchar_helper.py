from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_uint, r_ulonglong, intmask
from rpython.rtyper.annlowlevel import llunicode
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.rstr import copy_unicode_to_raw

SIZE_UNICODE = rffi.sizeof(lltype.UniChar)


if SIZE_UNICODE == 4:
    def ordinal_to_unicode(ordinal):    # 'ordinal' is a r_uint
        return unichr(intmask(ordinal))
else:
    def ordinal_to_unicode(ordinal):    # 'ordinal' is a r_uint
        if ordinal <= 0xffff:
            return unichr(intmask(ordinal))
        elif ordinal <= 0x10ffff:
            ordinal = intmask(ordinal - 0x10000)
            return (unichr(0xD800 | (ordinal >> 10)) +
                    unichr(0xDC00 | (ordinal & 0x3FF)))
        else:
            raise OutOfRange(ordinal)

def is_surrogate(u, index):
    return (unichr(0xD800) <= u[index + 0] <= unichr(0xDBFF) and
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
    ordinal = 0

    def __init__(self, ordinal):
        ordinal = intmask(rffi.cast(rffi.INT, ordinal))
        self.ordinal = ordinal

def _unicode_from_wchar(ptr, length):
    return rffi.wcharpsize2unicode(rffi.cast(rffi.CWCHARP, ptr), length)


if SIZE_UNICODE == 2:
    def unicode_from_char32(ptr, length):
        # 'ptr' is a pointer to 'length' 32-bit integers
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

    unicode_from_char16 = _unicode_from_wchar

else:
    unicode_from_char32 = _unicode_from_wchar

    def unicode_from_char16(ptr, length):
        # 'ptr' is a pointer to 'length' 16-bit integers
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


def unicode_size_as_char16(u):
    result = len(u)
    if SIZE_UNICODE == 4:
        for i in range(result):
            if ord(u[i]) > 0xFFFF:
                result += 1
    return result

def unicode_size_as_char32(u):
    result = len(u)
    if SIZE_UNICODE == 2 and result > 1:
        for i in range(result - 1):
            if is_surrogate(u, i):
                result -= 1
    return result


def _unicode_to_wchar(u, target_ptr, target_length, add_final_zero):
    # 'target_ptr' is a raw pointer to 'target_length' wchars;
    # we assume here that target_length == len(u).
    unichardata = rffi.cast(rffi.CWCHARP, target_ptr)
    copy_unicode_to_raw(llunicode(u), unichardata, 0, target_length)
    if add_final_zero:
        unichardata[target_length] = u'\x00'


if SIZE_UNICODE == 2:
    def unicode_to_char32(u, target_ptr, target_length, add_final_zero):
        # 'target_ptr' is a raw pointer to 'target_length' 32-bit integers;
        # we assume here that target_length == unicode_size_as_char32(u).
        ptr = rffi.cast(rffi.UINTP, target_ptr)
        src_index = 0
        last_surrogate_pos = len(u) - 2
        for i in range(target_length):
            if src_index <= last_surrogate_pos and is_surrogate(u, src_index):
                ordinal = as_surrogate(u, src_index)
                src_index += 2
            else:
                ordinal = r_uint(ord(u[src_index]))
                src_index += 1
            ptr[i] = rffi.cast(rffi.UINT, ordinal)
        if add_final_zero:
            ptr[target_length] = rffi.cast(rffi.UINT, 0)

    unicode_to_char16 = _unicode_to_wchar

else:
    unicode_to_char32 = _unicode_to_wchar

    def unicode_to_char16(u, target_ptr, target_length, add_final_zero):
        # 'target_ptr' is a raw pointer to 'target_length' 16-bit integers;
        # we assume here that target_length == unicode_size_as_char16(u).
        ptr = rffi.cast(rffi.USHORTP, target_ptr)
        for uc in u:
            ordinal = ord(uc)
            if ordinal > 0xFFFF:
                if ordinal > 0x10FFFF:
                    raise OutOfRange(ordinal)
                ordinal -= 0x10000
                ptr[0] = rffi.cast(rffi.USHORT, 0xD800 | (ordinal >> 10))
                ptr[1] = rffi.cast(rffi.USHORT, 0xDC00 | (ordinal & 0x3FF))
                ptr = rffi.ptradd(ptr, 2)
            else:
                ptr[0] = rffi.cast(rffi.USHORT, ordinal)
                ptr = rffi.ptradd(ptr, 1)
        assert ptr == (
            rffi.ptradd(rffi.cast(rffi.USHORTP, target_ptr), target_length))
        if add_final_zero:
            ptr[0] = rffi.cast(rffi.USHORT, 0)
