from pypy.interpreter.gateway import unwrap_spec
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib import rzipfile

@unwrap_spec(data='bufferstr', oldcrc='truncatedint_w')
def crc32(space, data, oldcrc=0):
    "Compute the CRC-32 incrementally."

    crc = rzipfile.crc32(data, r_uint(oldcrc))
    crc = rffi.cast(rffi.INT, crc)    # unsigned => 32-bit signed
    return space.wrap(intmask(crc))
