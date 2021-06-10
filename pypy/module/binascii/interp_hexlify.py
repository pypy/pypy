from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import unwrap_spec
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.rarithmetic import ovfcheck
from pypy.module.binascii.interp_binascii import raise_Error
from pypy.module.binascii.interp_binascii import AsciiBufferUnwrapper

# ____________________________________________________________

def _value2char(value):
    if value < 10:
        return chr(ord('0') + value)
    else:
        return chr((ord('a')-10) + value)
_value2char._always_inline_ = True

@unwrap_spec(data='bufferstr', bytes_per_sep=int)
def hexlify(space, data, w_sep=None, bytes_per_sep=0):
    '''Hexadecimal representation of binary data.

  sep
    An optional single character or byte to separate hex bytes.
  bytes_per_sep
    How many bytes between separators.  Positive values count from the
    right, negative values count from the left.

The return value is a bytes object.  This function is also
available as "b2a_hex()".'''
    from pypy.objspace.std.bytearrayobject import _array_to_hexstring
    from pypy.interpreter.buffer import SimpleView, StringBuffer
    if w_sep is not None:
        if not space.int_w(space.len(w_sep)) == 1:
            raise oefmt(space.w_ValueError, "sep must be length 1.")
        sep = space.text_w(w_sep)
    else:
        sep = None
    return _array_to_hexstring(space, StringBuffer(data), 0, 1,
                               len(data), sep=sep, bytes_per_sep=bytes_per_sep)

# ____________________________________________________________

def _char2value(space, c):
    if c <= '9':
        if c >= '0':
            return ord(c) - ord('0')
    elif c <= 'F':
        if c >= 'A':
            return ord(c) - (ord('A')-10)
    elif c <= 'f':
        if c >= 'a':
            return ord(c) - (ord('a')-10)
    raise_Error(space, 'Non-hexadecimal digit found')
_char2value._always_inline_ = True

@unwrap_spec(hexstr=AsciiBufferUnwrapper)
def unhexlify(space, hexstr):
    '''Binary data of hexadecimal representation.
hexstr must contain an even number of hex digits (upper or lower case).
This function is also available as "unhexlify()".'''
    if len(hexstr) & 1:
        raise_Error(space, 'Odd-length string')
    res = StringBuilder(len(hexstr) >> 1)
    for i in range(0, len(hexstr), 2):
        a = _char2value(space, hexstr[i])
        b = _char2value(space, hexstr[i+1])
        res.append(chr((a << 4) | b))
    return space.newbytes(res.build())
