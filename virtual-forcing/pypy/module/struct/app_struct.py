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

# XXX inefficient
class Struct(object):
    def __init__(self, format):
        self.format = format
        self.size = struct.calcsize(format)

    def pack(self, *args):
        return struct.pack(self.format, *args)

    def unpack(self, s):
        return struct.unpack(self.format, s)

    def pack_into(self, buffer, offset, *args):
        return pack_into(self.format, buffer, offset, *args)

    def unpack_from(self, buffer, offset=0):
        return unpack_from(self.format, buffer, offset)
