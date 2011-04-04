from pypy.interpreter.gateway import unwrap_spec
from pypy.rlib.rstring import StringBuilder
from pypy.module.binascii.interp_binascii import raise_Error

# ____________________________________________________________

def _a2b_read(space, s, index):
    try:
        c = s[index]
    except IndexError:
        return 0
    # Check the character for legality.  The 64 instead of the expected 63
    # is because there are a few uuencodes out there that use '`' as zero
    # instead of space.
    if c < ' ' or c > chr(32 + 64):
        if c == '\n' or c == '\r':
            return 0
        raise_Error(space, "Illegal char")
    return (ord(c) - 0x20) & 0x3f
_a2b_read._always_inline_ = True

def _a2b_write(space, res, length, char):
    if res.getlength() < length:    # common case: we have enough room.
        res.append(chr(char))
    else:
        # overflows.  Only accept zeros from now on.
        if char != 0:
            raise_Error(space, "Trailing garbage")
_a2b_write._always_inline_ = True


@unwrap_spec(ascii='bufferstr')
def a2b_uu(space, ascii):
    "Decode a line of uuencoded data."

    if len(ascii) == 0:    # obscure case, for compability with CPython
        length = (-0x20) & 0x3f
    else:
        length = (ord(ascii[0]) - 0x20) & 0x3f
    res = StringBuilder(length)

    for i in range(1, len(ascii), 4):
        A = _a2b_read(space, ascii, i)
        B = _a2b_read(space, ascii, i+1)
        C = _a2b_read(space, ascii, i+2)
        D = _a2b_read(space, ascii, i+3)
        #
        _a2b_write(space, res, length, A << 2 | B >> 4)
        _a2b_write(space, res, length, (B & 0xf) << 4 | C >> 2)
        _a2b_write(space, res, length, (C & 0x3) << 6 | D)

    remaining = length - res.getlength()
    if remaining > 0:
        res.append_multiple_char('\x00', remaining)
    return space.wrap(res.build())

# ____________________________________________________________

def _b2a_read(bin, i):
    try:
        return ord(bin[i])
    except IndexError:
        return 0
_a2b_read._always_inline_ = True

@unwrap_spec(bin='bufferstr')
def b2a_uu(space, bin):
    "Uuencode a line of data."

    length = len(bin)
    if length > 45:
        raise_Error(space, 'At most 45 bytes at once')
    res = StringBuilder(2 + ((length + 2) // 3) * 4)
    res.append(chr(0x20 + length))

    for i in range(0, length, 3):
        A = _b2a_read(bin, i)
        B = _b2a_read(bin, i+1)
        C = _b2a_read(bin, i+2)
        #
        res.append(chr(0x20 +                  (A >> 2)))
        res.append(chr(0x20 + ((A & 0x3) << 4 | B >> 4)))
        res.append(chr(0x20 + ((B & 0xF) << 2 | C >> 6)))
        res.append(chr(0x20 +  (C & 0x3F)))

    res.append('\n')
    return space.wrap(res.build())
