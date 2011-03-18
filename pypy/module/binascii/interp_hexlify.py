from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.rarithmetic import ovfcheck

# ____________________________________________________________

def _value2char(value):
    if value < 10:
        return chr(ord('0') + value)
    else:
        return chr((ord('a')-10) + value)
_value2char._always_inline_ = True

@unwrap_spec(data='bufferstr')
def hexlify(space, data):
    '''Hexadecimal representation of binary data.
This function is also available as "hexlify()".'''
    try:
        newlength = ovfcheck(len(data) * 2)
    except OverflowError:
        raise OperationError(space.w_MemoryError, space.w_None)
    res = StringBuilder(newlength)
    for c in data:
        res.append(_value2char(ord(c) >> 4))
        res.append(_value2char(ord(c) & 0xf))
    return space.wrap(res.build())

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
    raise OperationError(space.w_TypeError,
                         space.wrap('Non-hexadecimal digit found'))
_char2value._always_inline_ = True

@unwrap_spec(hexstr='bufferstr')
def unhexlify(space, hexstr):
    '''Binary data of hexadecimal representation.
hexstr must contain an even number of hex digits (upper or lower case).
This function is also available as "unhexlify()".'''
    if len(hexstr) & 1:
        raise OperationError(space.w_TypeError,
                             space.wrap('Odd-length string'))
    res = StringBuilder(len(hexstr) >> 1)
    for i in range(0, len(hexstr), 2):
        a = _char2value(space, hexstr[i])
        b = _char2value(space, hexstr[i+1])
        res.append(chr((a << 4) | b))
    return space.wrap(res.build())
