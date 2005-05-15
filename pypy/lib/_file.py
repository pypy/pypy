import os, _sio

##    # This is not quite correct, since more letters are allowed after
##    # these. However, the following are the only starting strings allowed
##    # in the mode parameter.
##    modes = {
##        'r'  : os.O_RDONLY,
##        'rb' : os.O_RDONLY,
##        'rU' : os.O_RDONLY,
##        'U'  : os.O_RDONLY,
##        'w'  : os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
##        'wb' : os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
##        'a'  : os.O_WRONLY | os.O_CREAT | os.O_EXCL,
##        'ab' : os.O_WRONLY | os.O_CREAT | os.O_EXCL,
##        'r+' : os.O_RDWR,
##        'rb+': os.O_RDWR,
##        'r+b': os.O_RDWR,
##        'w+' : os.O_RDWR | os.O_CREAT | os.O_TRUNC,
##        'wb+': os.O_RDWR | os.O_CREAT | os.O_TRUNC,
##        'w+b': os.O_RDWR | os.O_CREAT | os.O_TRUNC,
##        'a+' : os.O_RDWR | os.O_CREAT | os.O_EXCL,
##        'ab+': os.O_RDWR | os.O_CREAT | os.O_EXCL,
##        'a+b': os.O_RDWR | os.O_CREAT | os.O_EXCL,
##        }
##    def __init__(self, filename, mode="r"):
##        self.filename = filename
##        self.mode = mode
##        try:
##            flag = DiskFile.modes[mode]
##        except KeyError:
##            raise ValueError, "mode should be 'r', 'r+', 'w', 'w+' or 'a+'"

##        O_BINARY = getattr(os, "O_BINARY", 0)
##        flag |= O_BINARY
##        try:
##            self.fd = os.open(filename, flag)
##        except OSError:
##            # Opening in mode 'a' or 'a+' and file already exists
##            flag = flag & (os.O_RDWR | O_BINARY)
##            self.fd = os.open(filename, flag)
##        if mode[0] == 'a':
##            try:
##                os.lseek(self.fd, 0, 2) # Move to end of file
##            except:
##                os.close(self.fd)
##                raise


from os import O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_TRUNC
O_BINARY = getattr(os, "O_BINARY", 0)

#          (basemode, plus)
OS_MODE = {('r', False): O_RDONLY,
           ('r', True):  O_RDWR,
           ('w', False): O_WRONLY | O_CREAT | O_TRUNC,
           ('w', True):  O_RDWR   | O_CREAT | O_TRUNC,
           ('a', False): O_WRONLY | O_CREAT,
           ('a', True):  O_RDWR   | O_CREAT,
           }


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

    def __init__(self, name, mode='r', bufsize=None):
        self._mode = mode
        self._name = name
        self._closed = True   # Until the file is successfully opened
        self.softspace = 0    # Required according to file object docs
        self.encoding = None  # This is not used internally by file objects

        if not mode or mode[0] not in ['r', 'w', 'a', 'U']:
            raise IOError('invalid mode : %s' % mode)

        if mode[0] == 'U':
            mode = 'r' + mode

        basemode  = mode[0]    # 'r', 'w' or 'a'
        plus      = False
        universal = False
        binary    = False

        for c in mode[1:]:
            if c == '+':
                plus = True
            elif c == 'U':
                universal = True
            elif c == 'b':
                binary = True
            else:
                break

        flag = OS_MODE[basemode, plus]
        if binary or universal:
            flag |= O_BINARY

        self.fd = os.open(name, flag)
        if basemode == 'a':
            try:
                os.lseek(self.fd, 0, 2)
            except OSError:
                pass

        self.stream = _sio.DiskFile(self.fd)
        self._closed = False

        reading = basemode == 'r' or plus
        writing = basemode != 'r' or plus

        if bufsize == 0:   # no buffering
            pass
        elif bufsize == 1:   # line-buffering
            if writing:
                self.stream = _sio.LineBufferingOutputStream(self.stream)
            if reading:
                self.stream = _sio.BufferingInputStream(self.stream)

        else:     # default or explicit buffer sizes
            if bufsize is not None and bufsize < 0:
                bufsize = None
            if writing:
                self.stream = _sio.BufferingOutputStream(self.stream, bufsize)
            if reading:
                self.stream = _sio.BufferingInputStream(self.stream, bufsize)

        if universal:     # Wants universal newlines
            if writing and os.linesep != '\n':
                self.stream = _sio.TextOutputFilter(self.stream)
            if reading:
                self.stream = _sio.TextInputFilter(self.stream)

    def getnewlines(self):
        "end-of-line convention used in this file"
        if isinstance(self.stream, _sio.TextInputFilter):
            return self.stream.getnewlines()
        else:
            return None

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
        if size < 0:
            return self.stream.readline()
        else:
            # XXX slow
            chars = []
            for i in xrange(size):
                char = self.stream.read(1)
                chars.append(char)
                if char == '' or char == '\n':
                    break
            return ''.join(chars)

    def readlines(self, size=-1):
        """readlines([size]) -> list of strings, each a line from the file.

Call readline() repeatedly and return a list of the lines so read.
The optional size argument, if given, is an approximate bound on the
total number of bytes in the lines returned."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
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
        if not isinstance(data, str):
            raise TypeError('write() argument must be a string (for now)')
        return self.stream.write(data)

    def writelines(self, sequence_of_strings):
        """writelines(sequence_of_strings) -> None.  Write the strings to the file.

Note that newlines are not added.  The sequence can be any iterable object
producing strings. This is equivalent to calling write() for each string."""
        if self._closed:
            raise ValueError('I/O operation on closed file')
        for line in sequence_of_strings:
            if not isinstance(line, str):
                raise TypeError('writelines() argument must be a list '
                                'of strings')
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
        if not self._closed:
            self._closed = True
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
        return os.isatty(self.fd)
