
import sys

class buffer(object):
    """buffer(object [, offset[, size]])

Create a new buffer object which references the given object.
The buffer will reference a slice of the target object from the
start of the object (or at the specified offset). The slice will
extend to the end of the target object (or with the specified size).
"""

    def __init__(self, object, offset=0, size=None):
        import struct, array
        if isinstance(object, str):
            pass
        elif isinstance(object, unicode):
            str_object = ""
            if sys.maxunicode == 65535:
                pack_code = "H"
            else:
                pack_code = "I"
            for char in object:
                str_object += struct.pack(pack_code, ord(char))
            object = str_object
        elif isinstance(object, buffer):
            object = object.buf
        elif isinstance(object, array.array):
            object = object.tostring()
        else:
            raise TypeError, "buffer object expected"
        if offset < 0:
            raise ValueError, "offset must be zero or positive"
        # XXX according to CPython 2.4.1. Broken?
        if size is not None and size < -1:
            raise ValueError, "size must be zero or positive"
            
        if size is None or size == -1:
            self.buf = object[offset:]
        else:
            self.buf = object[offset:offset+size]

    def __str__(self):
        return self.buf

    def __add__(self, other):
        return self.buf + buffer(other).buf

    def __mul__(self, count):
        return self.buf * count

    __rmul__ = __mul__

    def __cmp__(self, other):
        return cmp(self.buf, buffer(other).buf)

    def __getitem__(self, index_or_slice):
        return self.buf[index_or_slice]

    def __hash__(self):
        return hash(self.buf)

    def __len__(self):
        return len(self.buf)

    def __repr__(self):
        # We support only read-only buffers anyway
        return "<read-only buffer for 0x000000>"
