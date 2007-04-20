"""NOT_RPYTHON"""

import sys
import _file


class file(object):
    """file(name[, mode[, buffering]]) -> file object

Open a file.  The mode can be 'r', 'w' or 'a' for reading (default),
writing or appending.  The file will be created if it doesn't exist
when opened for writing or appending; it will be truncated when
opened for writing.  Add a 'b' to the mode for binary files.
Add a '+' to the mode to allow simultaneous reading and writing.
If the buffering argument is given, 0 means unbuffered, 1 means line
buffered, and larger numbers specify the buffer size.
Add a 'U' to mode to open the file for input with universal newline
support.  Any line ending in the input file will be seen as a '\n'
in Python.  Also, a file so opened gains the attribute 'newlines';
the value for this attribute is one of None (no newline read yet),
'\r', '\n', '\r\n' or a tuple containing all the newline types seen.

Note:  open() is an alias for file().
    """

    _closed = True   # Until the file is successfully opened

    def __init__(self, name, mode='r', buffering=-1):
        stream = _file.open_file_as_stream(name, mode, buffering)
        fd = stream.try_to_find_file_descriptor()
        assert fd != -1
        self._fdopenstream(fd, mode, buffering, name, stream)

    def fdopen(cls, fd, mode='r', buffering=-1):
        f = cls.__new__(cls)
        stream = _file.fdopen_as_stream(fd, mode, buffering)
        f._fdopenstream(fd, mode, buffering, '<fdopen>', stream)
        return f
    fdopen = classmethod(fdopen)

    def _fdopenstream(self, fd, mode, buffering, name, stream):
        self.fd = fd
        self._name = name
        self.softspace = 0    # Required according to file object docs
        self.encoding = None  # This is not used internally by file objects
        self._closed = False
        self.stream = stream
        self._mode = mode
        if stream.flushable():
            sys.pypy__exithandlers__[stream] = stream.flush

    def getnewlines(self):
        "end-of-line convention used in this file"

        newlines = self.stream.getnewlines()
        if newlines == 0:
            return None
        if newlines in [1, 2, 4]:
            if newlines == 1:
                return "\r"
            elif newlines == 2:
                return "\n"
            else:
                return "\r\n"
        result = []
        if newlines & 1:
            result.append('\r')
        if newlines & 2:
            result.append('\n')
        if newlines & 4:
            result.append('\r\n')
        return tuple(result)

    mode     = property(lambda self: self._mode,
                        doc = "file mode ('r', 'U', 'w', 'a', "
                              "possibly with 'b' or '+' added)")
    name     = property(lambda self: self._name, doc = "file name")
    closed   = property(lambda self: self._closed,
                        doc = "True if the file is closed")
    newlines = property(lambda self: self.getnewlines(),
                        doc = "end-of-line convention used in this file")

    def read(self, n=-1):
        """read([size]) -> read at most size bytes, returned as a string.

If the size argument is negative or omitted, read until EOF is reached.
Notice that when in non-blocking mode, less data than what was requested
may be returned, even if no size parameter was given."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        if not isinstance(n, (int, long)):
            raise TypeError("an integer is required")
        if n < 0:
            return self.stream.readall()
        else:
            result = []
            while n > 0:
                data = self.stream.read(n)
                if not data:
                    break
                n -= len(data)
                result.append(data)
            return ''.join(result)

    def readline(self, size=-1):
        """readline([size]) -> next line from the file, as a string.

Retain newline.  A non-negative size argument limits the maximum
number of bytes to return (an incomplete line may be returned then).
Return an empty string at EOF."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        if not isinstance(size, (int, long)):
            raise TypeError("an integer is required")
        if size < 0:
            return self.stream.readline()
        else:
            # very inefficient unless there is a peek()
            result = []
            while size > 0:
                # "peeks" on the underlying stream to see how many characters
                # we can safely read without reading past an end-of-line
                peeked = self.stream.peek()
                pn = peeked.find("\n", 0, size)
                if pn < 0:
                    pn = min(size-1, len(peeked))
                c = self.stream.read(pn + 1)
                if not c:
                    break
                result.append(c)
                if c.endswith('\n'):
                    break
                size -= len(c)
            return ''.join(result)

    def readlines(self, size=-1):
        """readlines([size]) -> list of strings, each a line from the file.

Call readline() repeatedly and return a list of the lines so read.
The optional size argument, if given, is an approximate bound on the
total number of bytes in the lines returned."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        if not isinstance(size, (int, long)):
            raise TypeError("an integer is required")
        if size < 0:
            return list(iter(self.stream.readline, ""))
        else:
            result = []
            while size > 0:
                line = self.stream.readline()
                if not line:
                    break
                result.append(line)
                size -= len(line)
            return result

    def write(self, data):
        """write(str) -> None.  Write string str to file.

Note that due to buffering, flush() or close() may be needed before
the file on disk reflects the data written."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        return self.stream.write(data)

    def writelines(self, sequence_of_strings):
        """writelines(sequence_of_strings) -> None.  Write the strings to the file.

Note that newlines are not added.  The sequence can be any iterable object
producing strings. This is equivalent to calling write() for each string."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        for line in sequence_of_strings:
            self.stream.write(line)

    def tell(self):
        """tell() -> current file position, an integer (may be a long integer)."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        return self.stream.tell()
    
    def seek(self, offset, whence=0):
        """seek(offset[, whence]) -> None.  Move to new file position.

Argument offset is a byte count.  Optional argument whence defaults to
0 (offset from start of file, offset should be >= 0); other values are 1
(move relative to current position, positive or negative), and 2 (move
relative to end of file, usually negative, although many platforms allow
seeking beyond the end of a file).  If the file is opened in text mode,
only offsets returned by tell() are legal.  Use of other offsets causes
undefined behavior.
Note that not all file objects are seekable."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        self.stream.seek(offset, whence)

    def __iter__(self):
        """Iterating over files, as in 'for line in f:', returns each line of
the file one by one."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        return self
    xreadlines = __iter__
    
    def next(self):
        """next() -> the next line in the file, or raise StopIteration"""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        line = self.stream.readline()
        if line == '':
            raise StopIteration
        return line

    def truncate(self, size=None):
        """truncate([size]) -> None.  Truncate the file to at most size bytes.

Size defaults to the current file position, as returned by tell()."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        if size is None:
            size = self.stream.tell()
        self.stream.truncate(size)

    def flush(self):
        """flush() -> None.  Flush the internal I/O buffer."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        self.stream.flush()

    def close(self):
        """close() -> None or (perhaps) an integer.  Close the file.

Sets data attribute .closed to True.  A closed file cannot be used for
further I/O operations.  close() may be called more than once without
error.  Some kinds of file objects (for example, opened by popen())
may return an exit status upon closing."""
        if not self._closed and hasattr(self, 'stream'):
            self._closed = True
            sys.pypy__exithandlers__.pop(self.stream, None)
            self.stream.close()

    __del__ = close

    def readinto(self, a):
        """readinto() -> Undocumented.  Don't use this; it may go away."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        from array import array
        if not isinstance(a, array):
            raise TypeError('Can only read into array objects')
        length = len(a)
        data = self.read(length)
        del a[:]
        a.fromstring(data + '\x00' * (length-len(data)))
        return len(data)

    def fileno(self):
        '''fileno() -> integer "file descriptor".

This is needed for lower-level file interfaces, such os.read().'''
        if self._closed:
            raise ValueError('I/O operation on closed file')
        return self.fd

    def isatty(self):
        """isatty() -> true or false.  True if the file is connected to a tty device."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        import os
        return os.isatty(self.fd)

    def __repr__(self):
        return "<%s file '%s', mode %r at 0x%x>" % (
            self._closed and 'closed' or 'open',
            self._name,
            self._mode,
            id(self))
