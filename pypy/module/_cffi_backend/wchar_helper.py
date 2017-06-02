from rpython.rlib.rarithmetic import r_uint, r_ulonglong, intmask
from rpython.rtyper.lltypesystem import lltype, rffi

SIZE_UNICHAR = rffi.sizeof(lltype.UniChar)


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
