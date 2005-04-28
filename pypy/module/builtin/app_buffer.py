# Might probably be deprecated in Python at some point.

class buffer(object):
    """buffer(object [, offset[, size]])

Create a new buffer object which references the given object.
The buffer will reference a slice of the target object from the
start of the object (or at the specified offset). The slice will
extend to the end of the target object (or with the specified size).
"""

    def __init__(self, object, offset=0, size=None):
        if isinstance(object, str):
            pass
        elif isinstance(object, buffer):
            object = object.buf
        else:
            # XXX check for more types
            raise TypeError, "buffer object expected"
        if offset < 0:
            raise ValueError, "offset must be zero or positive"
            
        if size is None:
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
