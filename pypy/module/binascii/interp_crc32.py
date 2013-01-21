from pypy.interpreter.gateway import unwrap_spec
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rzipfile import crc_32_tab

@unwrap_spec(data='bufferstr', oldcrc='truncatedint_w')
def crc32(space, data, oldcrc=0):
    "Compute the CRC-32 incrementally."

    crc = r_uint(rffi.cast(rffi.UINT, ~oldcrc))   # signed => 32-bit unsigned

    # in the following loop, we have always 0 <= crc < 2**32
    for c in data:
        crc = crc_32_tab[(crc & 0xff) ^ ord(c)] ^ (crc >> 8)

    crc = ~intmask(rffi.cast(rffi.INT, crc))   # unsigned => 32-bit signed
    return space.wrap(crc)
