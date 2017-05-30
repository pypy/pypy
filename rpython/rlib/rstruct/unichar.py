"""
Helpers to pack and unpack a unicode character into raw bytes.
"""

import sys
from rpython.rlib.runicode import MAXUNICODE

if MAXUNICODE <= 65535:
    UNICODE_SIZE = 2
else:
    UNICODE_SIZE = 4
BIGENDIAN = sys.byteorder == "big"

def pack_unichar(unich, buf, pos):
    if UNICODE_SIZE == 2:
        if BIGENDIAN:
            buf.setitem(pos,   chr(ord(unich) >> 8))
            buf.setitem(pos+1, chr(ord(unich) & 0xFF))
        else:
            buf.setitem(pos,   chr(ord(unich) & 0xFF))
            buf.setitem(pos+1, chr(ord(unich) >> 8))
    else:
        if BIGENDIAN:
            buf.setitem(pos,   chr(ord(unich) >> 24))
            buf.setitem(pos+1, chr((ord(unich) >> 16) & 0xFF))
            buf.setitem(pos+2, chr((ord(unich) >> 8) & 0xFF))
            buf.setitem(pos+3, chr(ord(unich) & 0xFF))
        else:
            buf.setitem(pos,   chr(ord(unich) & 0xFF))
            buf.setitem(pos+1, chr((ord(unich) >> 8) & 0xFF))
            buf.setitem(pos+2, chr((ord(unich) >> 16) & 0xFF))
            buf.setitem(pos+3, chr(ord(unich) >> 24))

def unpack_unichar(rawstring):
    assert len(rawstring) == UNICODE_SIZE
    if UNICODE_SIZE == 2:
        if BIGENDIAN:
            n = (ord(rawstring[0]) << 8 |
                 ord(rawstring[1]))
        else:
            n = (ord(rawstring[0]) |
                 ord(rawstring[1]) << 8)
    else:
        if BIGENDIAN:
            n = (ord(rawstring[0]) << 24 |
                 ord(rawstring[1]) << 16 |
                 ord(rawstring[2]) << 8 |
                 ord(rawstring[3]))
        else:
            n = (ord(rawstring[0]) |
                 ord(rawstring[1]) << 8 |
                 ord(rawstring[2]) << 16 |
                 ord(rawstring[3]) << 24)
    return unichr(n)
