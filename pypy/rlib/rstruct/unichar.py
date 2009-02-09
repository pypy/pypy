"""
Helpers to pack and unpack a unicode character into raw bytes.
"""

import sys
from pypy.rlib.runicode import MAXUNICODE

if MAXUNICODE <= 65535:
    UNICODE_SIZE = 2
else:
    UNICODE_SIZE = 4
BIGENDIAN = sys.byteorder == "big"

def pack_unichar(unich, charlist):
    if UNICODE_SIZE == 2:
        if BIGENDIAN:
            charlist.append(chr(ord(unich) >> 8))
            charlist.append(chr(ord(unich) & 0xFF))
        else:
            charlist.append(chr(ord(unich) & 0xFF))
            charlist.append(chr(ord(unich) >> 8))
    else:
        if BIGENDIAN:
            charlist.append(chr(ord(unich) >> 24))
            charlist.append(chr((ord(unich) >> 16) & 0xFF))
            charlist.append(chr((ord(unich) >> 8) & 0xFF))
            charlist.append(chr(ord(unich) & 0xFF))
        else:
            charlist.append(chr(ord(unich) & 0xFF))
            charlist.append(chr((ord(unich) >> 8) & 0xFF))
            charlist.append(chr((ord(unich) >> 16) & 0xFF))
            charlist.append(chr(ord(unich) >> 24))

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
