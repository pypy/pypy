# NOT_RPYTHON
"""
Application-level definitions for the struct module.
"""
import struct

class error(Exception):
    """Exception raised on various occasions; argument is a string
    describing what is wrong."""

# XXX inefficient
def pack_into(fmt, buf, offset, *args):
    data = struct.pack(fmt, *args)
    buffer(buf)[offset:offset+len(data)] = data

# XXX inefficient
def unpack_from(fmt, buf, offset=0):
    size = struct.calcsize(fmt)
    data = buffer(buf)[offset:offset+size]
    if len(data) != size:
        raise error("unpack_from requires a buffer of at least %d bytes"
                    % (size,))
    return struct.unpack(fmt, data)
