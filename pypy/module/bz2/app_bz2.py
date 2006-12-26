__doc__ = """The python bz2 module provides a comprehensive interface for
the bz2 compression library. It implements a complete file
interface, one shot (de)compression functions, and types for
sequential (de)compression."""


class BZ2File(file):
    """BZ2File(name [, mode='r', buffering=0, compresslevel=9]) -> file object
    
    Open a bz2 file. The mode can be 'r' or 'w', for reading (default) or
    writing. When opened for writing, the file will be created if it doesn't
    exist, and truncated otherwise. If the buffering argument is given, 0 means
    unbuffered, and larger numbers specify the buffer size. If compresslevel
    is given, must be a number between 1 and 9.

    Add a 'U' to mode to open the file for input with universal newline
    support. Any line ending in the input file will be seen as a '\\n' in
    Python. Also, a file so opened gains the attribute 'newlines'; the value
    for this attribute is one of None (no newline read yet), '\\r', '\\n',
    '\\r\\n' or a tuple containing all the newline types seen. Universal
    newlines are available only when reading."""
    def __init__(self, name, mode='r', buffering=-1, compresslevel=9):
        import bz2
        # the stream should always be opened in binary mode
        if "b" not in mode:
            mode = mode + "b"
        self._name = name
        self.softspace = 0    # Required according to file object docs
        self.encoding = None  # This is not used internally by file objects
        self._closed = False
        self.stream = bz2._open_file_as_stream(self._name, mode, buffering,
                                               compresslevel)
        self._mode = mode
        self.fd = self.stream.try_to_find_file_descriptor()
        assert self.fd != -1

    def fdopen(cls, fd, mode='r', buffering=-1):
        raise TypeError("fdopen not supported by BZ2File")
    fdopen = classmethod(fdopen)

    def __repr__(self):
        return '<%s bz2.BZ2File %r, mode %r at 0x%x>' % (
            self._closed and 'closed' or 'open',
            self._name,
            self._mode,
            id(self))
