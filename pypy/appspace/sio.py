"""New standard I/O library.

This code is still very young and experimental!

There are fairly complete unit tests in test_sio.py.

The design is simple:

- A raw stream supports read(n), write(s), seek(offset, whence=0) and
  tell().  This is generally unbuffered.  Raw streams may support
  Unicode.

- A basis stream provides the raw stream API and builds on a much more
  low-level API, e.g. the os, mmap or socket modules.

- A filtering stream is raw stream built on top of another raw stream.
  There are filtering streams for universal newline translation and
  for unicode translation.

- A buffering stream supports the full classic Python I/O API:
  read(n=-1), readline(), readlines(sizehint=0), tell(), seek(offset,
  whence=0), write(s), writelines(lst), as well as __iter__() and
  next().  (There's also readall() but that's a synonym for read()
  without arguments.)  This is a superset of the raw stream API.  I
  haven't thought about fileno() and isatty() yet, nor about
  truncate() or the various attributes like name and mode.  Also,
  close() is not implemented right.  We really need only one buffering
  stream implementation, which is a filtering stream.

You typically take a basis stream, place zero or more filtering
streams on top of it, and then top it off with a buffering stream.

"""

import os

class Stream(object):
    "All streams except the base ones need to inherit from this class."
    base = None
    def __getattr__(self, name):
        """
        Delegate all other methods to the underlying file object.
        """
        return getattr(self.base, name)

class BufferingInputStream(Stream):

    """Standard buffering input stream.

    This is typically the top of the stack.
    """

    bigsize = 2**19 # Half a Meg
    bufsize = 2**13 # 8 K

    def __init__(self, base, bufsize=None):
        self.do_read = getattr(base, "read", None)
                       # function to fill buffer some more
        self.do_tell = getattr(base, "tell", None)
                       # None, or return a byte offset 
        self.do_seek = getattr(base, "seek", None)
                       # None, or seek to a byte offset
        self.close = base.close

        if bufsize is None:     # Get default from the class
            bufsize = self.bufsize
        self.bufsize = bufsize  # buffer size (hint only)
        self.lines = []         # ready-made lines (sans "\n")
        self.buf = ""           # raw data (may contain "\n")
        # Invariant: readahead == "\n".join(self.lines + [self.buf])
        # self.lines contains no "\n"
        # self.buf may contain "\n"

    def tell(self):
        bytes = self.do_tell()  # This may fail
        offset = len(self.buf)
        for line in self.lines:
            offset += len(line) + 1
        assert bytes >= offset, (locals(), self.__dict__)
        return bytes - offset

    def seek(self, offset, whence=0):
        # This may fail on the do_seek() or do_tell() call.
        # But it won't call either on a relative forward seek.
        # Nor on a seek to the very end.
        if whence == 0 or (whence == 2 and self.do_seek is not None):
            self.do_seek(offset, whence)
            self.lines = []
            self.buf = ""
            return
        if whence == 2:
            # Skip relative to EOF by reading and saving only just as
            # much as needed
            assert self.do_seek is None
            data = "\n".join(self.lines + [self.buf])
            total = len(data)
            buffers = [data]
            self.lines = []
            self.buf = ""
            while 1:
                data = self.do_read(self.bufsize)
                if not data:
                    break
                buffers.append(data)
                total += len(data)
                while buffers and total >= len(buffers[0]) - offset:
                    total -= len(buffers[0])
                    del buffers[0]
            cutoff = total + offset
            if cutoff < 0:
                raise TypeError, "cannot seek back"
            if buffers:
                buffers[0] = buffers[0][cutoff:]
            self.buf = "".join(buffers)
            self.lines = []
            return
        if whence == 1:
            if offset < 0:
                self.do_seek(self.tell() + offset, 0)
                self.lines = []
                self.buf = ""
                return
            while self.lines:
                line = self.lines[0]
                if offset <= len(line):
                    self.lines[0] = line[offset:]
                    return
                offset -= len(self.lines[0]) - 1
                del self.lines[0]
            assert not self.lines
            if offset <= len(self.buf):
                self.buf = self.buf[offset:]
                return
            offset -= len(self.buf)
            self.buf = ""
            if self.do_seek is None:
                self.read(offset)
            else:
                self.do_seek(offset, 1)
            return
        raise ValueError, "whence should be 0, 1 or 2"

    def readall(self):
        self.lines.append(self.buf)
        more = ["\n".join(self.lines)]
        self.lines = []
        self.buf = ""
        bufsize = self.bufsize
        while 1:
            data = self.do_read(bufsize)
            if not data:
                break
            more.append(data)
            bufsize = max(bufsize*2, self.bigsize)
        return "".join(more)

    def read(self, n=-1):
        if n < 0:
            return self.readall()

        if self.lines:
            # See if this can be satisfied from self.lines[0]
            line = self.lines[0]
            if len(line) >= n:
                self.lines[0] = line[n:]
                return line[:n]

            # See if this can be satisfied *without exhausting* self.lines
            k = 0
            i = 0
            for line in self.lines:
                k += len(line)
                if k >= n:
                    lines = self.lines[:i]
                    data = self.lines[i]
                    cutoff = len(data) - (k-n)
                    lines.append(data[:cutoff])
                    self.lines[:i+1] = [data[cutoff:]]
                    return "\n".join(lines)
                k += 1
                i += 1

            # See if this can be satisfied from self.lines plus self.buf
            if k + len(self.buf) >= n:
                lines = self.lines
                self.lines = []
                cutoff = n - k
                lines.append(self.buf[:cutoff])
                self.buf = self.buf[cutoff:]
                return "\n".join(lines)

        else:
            # See if this can be satisfied from self.buf
            data = self.buf
            k = len(data)
            if k >= n:
                cutoff = len(data) - (k-n)
                self.buf = data[cutoff:]
                return data[:cutoff]

        lines = self.lines
        self.lines = []
        lines.append(self.buf)
        self.buf = ""
        data = "\n".join(lines)
        more = [data]
        k = len(data)
        while k < n:
            data = self.do_read(max(self.bufsize, n-k))
            k += len(data)
            more.append(data)
            if not data:
                break
        cutoff = len(data) - (k-n)
        self.buf = data[cutoff:]
        more[-1] = data[:cutoff]
        return "".join(more)

    def __iter__(self):
        return self

    def next(self):
        if self.lines:
            return self.lines.pop(0) + "\n"

        # This block is needed because read() can leave self.buf
        # containing newlines
        self.lines = self.buf.split("\n")
        self.buf = self.lines.pop()
        if self.lines:
            return self.lines.pop(0) + "\n"

        buf = self.buf and [self.buf] or []
        while 1:
            self.buf = self.do_read(self.bufsize)
            self.lines = self.buf.split("\n")
            self.buf = self.lines.pop()
            if self.lines:
                buf.append(self.lines.pop(0))
                buf.append("\n")
                break
            if not self.buf:
                break
            buf.append(self.buf)

        line = "".join(buf)
        if not line:
            raise StopIteration
        return line

    def readline(self):
        try:
            return self.next()
        except StopIteration:
            return ""

    def readlines(self, sizehint=0):
        return list(self)

class BufferingOutputStream(Stream):

    """Standard buffering output stream.

    This is typically the top of the stack.
    """

    bigsize = 2**19 # Half a Meg
    bufsize = 2**13 # 8 K

    def __init__(self, base, bufsize=None):
        self.base = base
        self.do_write = base.write # Flush buffer
        self.do_tell = base.tell
             # Return a byte offset; has to exist or this __init__() will fail
        self.do_seek = getattr(base, "seek", None)
                       # None, or seek to a byte offset
        self.do_close = base.close # Close file
        self.do_truncate = base.truncate # Truncate file

        if bufsize is None:     # Get default from the class
            bufsize = self.bufsize
        self.bufsize = bufsize  # buffer size (hint only)
        self.buf = ""
        self.tell()
        
    def tell(self):
        assert self.do_tell is not None
        if not hasattr(self, 'pos'):
            self.pos = self.do_tell()

        return self.pos
            
    def seek(self, offset, whence=0):
        self.flush()
        self.do_seek(offset, whence)
        self.pos = self.do_tell()

    def flush(self):
        self.do_write(self.buf)
        self.buf = ''
     
    def write(self, data):
        buflen = len(self.buf)
        datalen = len(data)
        if  datalen + buflen < self.bufsize:
            self.buf += data
            self.pos += datalen
        else:
            self.buf += data[:self.bufsize-buflen]
            self.pos += self.bufsize-buflen
            self.do_write(self.buf)
            self.buf = ''
            self.write(data[self.bufsize-buflen:])

    def writelines(self, sequence):
        for s in sequence:
            self.write(s)
            
    def close(self):
        self.do_write(self.buf)
        self.buf = ''
        if self.do_close():
            self.do_close()

    def truncate(self, size=None):
        self.flush()
        self.do_truncate(size)

class LineBufferingOutputStream(BufferingOutputStream):

    """Line buffering output stream.

    This is typically the top of the stack.
    """

    def __init__(self, base, bufsize=None):
        self.do_write = base.write # Flush buffer
        self.do_tell = base.tell
             # Return a byte offset; has to exist or this __init__() will fail
        self.do_seek = getattr(base, "seek", None)
                       # None, or seek to a byte offset
        self.do_close = base.close # Close file
        self.do_truncate = base.truncate # Truncate file

        self.linesep = os.linesep
        self.buf = ""           # raw data (may contain "\n")
        self.tell()
        
    def write(self, data):
        all_lines = data.split(self.linesep)
        full_lines = all_lines[:-1]
        for line in full_lines:
            line += self.linesep
            buflen = len(self.buf)
            linelen = len(line)
            if  linelen + buflen < self.bufsize:
                self.buf += line
                self.pos += linelen
                self.do_write(self.buf)
                self.buf = ''
            else:
                self.buf += line[:self.bufsize-buflen]
                self.pos += self.bufsize-buflen
                self.do_write(self.buf)
                self.buf = ''
                self.write(line[self.bufsize-buflen:])

        # The last part of the split data never has a terminating linesep.
        # If the data has a terminating linesep, the last element is an
        # empty string.

        line = all_lines[-1]
        buflen = len(self.buf)
        linelen = len(line)
        if  linelen + buflen < self.bufsize:
            self.buf += line
            self.pos += linelen
        else:
            self.buf += line[:self.bufsize-buflen]
            self.pos += self.bufsize-buflen
            self.do_write(self.buf)
            self.buf = ''
            self.write(line[self.bufsize-buflen:])
        
class BufferingInputOutputStream(Stream):
    """To handle buffered input and output at the same time, we are
       switching back and forth between using BuffereingInputStream
       and BufferingOutputStream as reads and writes are done.
       A more optimal solution would be to read and write on the same
       buffer, but it would take a fair bit of time to implement.
    """

    def __init__(self, base, bufsize=None):
        self.base = base
        self.bufsize = bufsize
        self.reader = None
        self.writer = None

    def read(self, n=-1):
        if not self.reader:
            if self.writer:
                self.writer.flush()
                self.writer = None
            self.reader = BufferingInputStream(self.base, self.bufsize)
        return self.reader.read(n)

    def write(self, data):
        if not self.writer:
            if self.reader:
                # Make sure the underlying file has the correct current
                # position
                self.reader.seek(self.reader.tell())
                self.reader = None
            self.writer = BufferingOutputStream(self.base, self.bufsize)
        return self.writer.write(data)

    def truncate(self, size=None):
        if not self.writer:
            if self.reader:
                # Make sure the underlying file has the correct current
                # position
                self.reader.seek(self.reader.tell())
                self.reader = None
            self.writer = BufferingOutputStream(self.base, self.bufsize)
        return self.writer.truncate(size)

    def __getattr__(self, name):
        """
        Delegate all other methods to the underlying file object.
        """
        if not self.reader and not self.writer:
            self.reader = BufferingInputStream(self.base, self.bufsize)

        if self.reader:
            return getattr(self.reader, name)
        
        return getattr(self.writer, name)

class CRLFFilter(Stream):

    """Filtering stream for universal newlines.

    TextInputFilter is more general, but this is faster when you don't
    need tell/seek.
    """

    def __init__(self, base):
        self.do_read = base.read
        self.atcr = False
        self.close = base.close

    def read(self, n):
        data = self.do_read(n)
        if self.atcr:
            if data.startswith("\n"):
                data = data[1:] # Very rare case: in the middle of "\r\n"
            self.atcr = False
        if "\r" in data:
            self.atcr = data.endswith("\r")     # Test this before removing \r
            data = data.replace("\r\n", "\n")   # Catch \r\n this first
            data = data.replace("\r", "\n")     # Remaining \r are standalone
        return data

class MMapFile(object):

    """Standard I/O basis stream using mmap."""

    def __init__(self, filename, mode="r"):
        import mmap
        self.filename = filename
        self.mode = mode
        if mode == "r":
            flag = os.O_RDONLY
            self.access = mmap.ACCESS_READ
        else:
            if mode == "w":
                flag = os.O_RDWR | os.O_CREAT
            elif mode == "a":
                flag = os.O_RDWR
            else:
                raise ValueError, "mode should be 'r', 'w' or 'a'"
            self.access = mmap.ACCESS_WRITE
        if hasattr(os, "O_BINARY"):
            flag |= os.O_BINARY
        self.fd = os.open(filename, flag)
        size = os.fstat(self.fd).st_size
        self.mm = mmap.mmap(self.fd, size, access=self.access)
        self.pos = 0

    def __del__(self):
        self.close()

    mm = fd = None

    def close(self):
        if self.mm is not None:
            self.mm.close()
            self.mm = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = max(0, offset)
        elif whence == 1:
            self.pos = max(0, self.pos + offset)
        elif whence == 2:
            self.pos = max(0, self.mm.size() + offset)
        else:
            raise ValueError, "seek(): whence must be 0, 1 or 2"

    def readall(self):
        return self.read()

    def read(self, n=-1):
        import mmap
        if n >= 0:
            aim = self.pos + n
        else:
            aim = self.mm.size() # Actual file size, may be more than mapped
            n = aim - self.pos
        data = self.mm[self.pos:aim]
        if len(data) < n:
            del data
            # File grew since opened; remap to get the new data
            size = os.fstat(self.fd).st_size
            self.mm = mmap.mmap(self.fd, size, access=self.access)
            data = self.mm[self.pos:aim]
        self.pos += len(data)
        return data

    def __iter__(self):
        return self

    def readline(self):
        import mmap
        hit = self.mm.find("\n", self.pos) + 1
        if hit:
            data = self.mm[self.pos:hit]
            self.pos = hit
            return data
        # Remap the file just in case
        size = os.fstat(self.fd).st_size
        self.mm = mmap.mmap(self.fd, size, access=self.access)
        hit = self.mm.find("\n", self.pos) + 1
        if hit:
            # Got a whole line after remapping
            data = self.mm[self.pos:hit]
            self.pos = hit
            return data
        # Read whatever we've got -- may be empty
        data = self.mm[self.pos:self.mm.size()]
        self.pos += len(data)
        return data

    def next(self):
        import mmap
        hit = self.mm.find("\n", self.pos) + 1
        if hit:
            data = self.mm[self.pos:hit]
            self.pos = hit
            return data
        # Remap the file just in case
        size = os.fstat(self.fd).st_size
        self.mm = mmap.mmap(self.fd, size, access=self.access)
        hit = self.mm.find("\n", self.pos) + 1
        if hit:
            # Got a whole line after remapping
            data = self.mm[self.pos:hit]
            self.pos = hit
            return data
        # Read whatever we've got -- may be empty
        data = self.mm[self.pos:self.mm.size()]
        if not data:
            raise StopIteration
        self.pos += len(data)
        return data

    def readlines(self, sizehint=0):
        return list(iter(self.readline, ""))

    def write(self, data):
        end = self.pos + len(data)
        try:
            self.mm[self.pos:end]  = data
            # This can raise IndexError on Windows, ValueError on Unix
        except (IndexError, ValueError):
            # XXX On Unix, this resize() call doesn't work
            self.mm.resize(end)
            self.mm[self.pos:end]  = data
        self.pos = end

    def writelines(self, lines):
        filter(self.write, lines)

class DiskFile(object):

    """Standard I/O basis stream using os.open/close/read/write/lseek"""

    # This is not quite correct, since more letters are allowed after
    # these. However, the following are the only starting strings allowed
    # in the mode parameter.
    modes = {
        'r'  : os.O_RDONLY,
        'rb' : os.O_RDONLY,
        'rU' : os.O_RDONLY,
        'U'  : os.O_RDONLY,
        'w'  : os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        'wb' : os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        'a'  : os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        'ab' : os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        'r+' : os.O_RDWR,
        'rb+': os.O_RDWR,
        'r+b': os.O_RDWR,
        'w+' : os.O_RDWR | os.O_CREAT | os.O_TRUNC,
        'wb+': os.O_RDWR | os.O_CREAT | os.O_TRUNC,
        'w+b': os.O_RDWR | os.O_CREAT | os.O_TRUNC,
        'a+' : os.O_RDWR | os.O_CREAT | os.O_EXCL,
        'ab+': os.O_RDWR | os.O_CREAT | os.O_EXCL,
        'a+b': os.O_RDWR | os.O_CREAT | os.O_EXCL,
        }
    def __init__(self, filename, mode="r"):
        self.filename = filename
        self.mode = mode
        try:
            flag = DiskFile.modes[mode]
        except KeyError:
            raise ValueError, "mode should be 'r', 'r+', 'w', 'w+' or 'a+'"

        O_BINARY = getattr(os, "O_BINARY", 0)
        flag |= O_BINARY
        try:
            self.fd = os.open(filename, flag)
        except OSError:
            # Opening in mode 'a' or 'a+' and file already exists
            flag = flag & (os.O_RDWR | O_BINARY)
            self.fd = os.open(filename, flag)
        if mode[0] == 'a':
            os.lseek(self.fd, 0, 2) # Move to end of file

    def seek(self, offset, whence=0):
        os.lseek(self.fd, offset, whence)

    def tell(self):
        return os.lseek(self.fd, 0, 1)

    def read(self, n):
        return os.read(self.fd, n)

    def write(self, data):
        while data:
            n = os.write(self.fd, data)
            data = data[n:]

    def close(self):
        fd = self.fd
        if fd is not None:
            self.fd = None
            os.close(fd)

    def truncate(self, size=None):
        if size is None:
            size = self.tell()
        if os.name == 'posix':
            os.ftruncate(self.fd, size)
        else:
            raise NotImplementedError
        
    def isatty(self):
        if os.name == 'posix':
            return os.isatty(self.fd)
        else:
            raise NotImplementedError
        
    def fileno():
        return self.fd
        
    def __del__(self):
        try:
            self.close()
        except:
            pass

class TextInputFilter(Stream):

    """Filtering input stream for universal newline translation."""

    def __init__(self, base):
        self.base = base   # must implement read, may implement tell, seek
        self.atcr = False  # Set when last char read was \r
        self.buf = ""      # Optional one-character read-ahead buffer
        self.close = base.close
        self.CR = False
        self.NL = False
        self.CRLF = False
        
    def __getattr__(self, name):
        if name == 'newlines':
            foundchars = self.CR * 1 + self.NL * 2 + self.CRLF * 4
            if  not foundchars:
                return None
            if foundchars in [1, 2, 4]:
                if self.CR:
                    return '\r'
                elif self.NL:
                    return '\n'
                else:
                    return '\r\n'
            else:
                result = []
                if self.CR:
                    result.append('\r')
                if self.NL:
                    result.append('\n')
                if self.CRLF:
                    result.append('\r\n')
                return tuple(result)
            
    def read(self, n):
        """Read up to n bytes."""
        if n <= 0:
            return ""
        if self.buf:
            assert not self.atcr
            data = self.buf
            self.buf = ""
            return data
        data = self.base.read(n)

        # The following whole ugly mess is because we need to keep track of
        # exactly which line separators we have seen for self.newlines,
        # grumble, grumble.  This has an interesting corner-case.
        #
        # Consider a file consisting of exactly one line ending with '\r'.
        # The first time you read(), you will not know whether it is a
        # CR separator or half of a CRLF separator.  Neither will be marked
        # as seen, since you are waiting for your next read to determine
        # what you have seen.  But there's no more to read ...
                        
        if self.atcr:
            if data.startswith("\n"):
                data = data[1:]
                self.CRLF = True
                if not data:
                    data = self.base.read(n)
            else:
                self.CR = True
            self.atcr = False
            
        for i in range(len(data)):
            if data[i] == '\n':
                if i > 0 and data[i-1] == '\r':
                    self.CRLF = True
                else:
                    self.NL = True
            elif data[i] == '\r':
                if i < len(data)-1 and data[i+1] != '\n':
                    self.CR = True
                    
        if "\r" in data:
            self.atcr = data.endswith("\r")
            data = data.replace("\r\n", "\n").replace("\r", "\n")
            
        return data

    def seek(self, offset, whence=0):
        """Seeks based on knowledge that does not come from a tell()
           may go to the wrong place, since the number of
           characters seen may not match the number of characters
           that are actually in the file (where \r\n is the
           line separator). Arithmetics on the result
           of a tell() that moves beyond a newline character may in the
           same way give the wrong result.
        """
        self.base.seek(offset, whence)
        self.atcr = False
        self.buf = ""

    def tell(self):
        pos = self.base.tell()
        if self.atcr:
            # Must read the next byte to see if it's \n,
            # because then we must report the next position.
            assert not self.buf 
            self.buf = self.base.read(1)
            pos += 1
            self.atcr = False
            if self.buf == "\n":
                self.buf = ""
        return pos - len(self.buf)

class TextOutputFilter(Stream):

    """Filtering output stream for universal newline translation."""

    def __init__(self, base, linesep=os.linesep):
        assert linesep in ["\n", "\r\n", "\r"]
        self.base = base    # must implement write, may implement seek, tell
        self.linesep = linesep
        self.close = base.close

    def write(self, data):
        if self.linesep is not "\n" and "\n" in data:
            data = data.replace("\n", self.linesep)
        self.base.write(data)

    def seek(self, offset, whence=0):
        self.base.seek(offset, whence)

    def tell(self):
        return self.base.tell()

class DecodingInputFilter(Stream):

    """Filtering input stream that decodes an encoded file."""

    def __init__(self, base, encoding="utf8", errors="strict"):
        self.base = base
        self.encoding = encoding
        self.errors = errors
        self.tell = base.tell
        self.seek = base.seek
        self.close = base.close

    def read(self, n):
        """Read *approximately* n bytes, then decode them.

        Under extreme circumstances,
        the return length could be longer than n!

        Always return a unicode string.

        This does *not* translate newlines;
        you can stack TextInputFilter.
        """
        data = self.base.read(n)
        try:
            return data.decode(self.encoding, self.errors)
        except ValueError:
            # XXX Sigh.  decode() doesn't handle incomplete strings well.
            # Use the retry strategy from codecs.StreamReader.
            for i in range(9):
                more = self.base.read(1)
                if not more:
                    raise
                data += more
                try:
                    return data.decode(self.encoding, self.errors)
                except ValueError:
                    pass
            raise

class EncodingOutputFilter(Stream):

    """Filtering output stream that writes to an encoded file."""

    def __init__(self, base, encoding="utf8", errors="strict"):
        self.base = base
        self.encoding = encoding
        self.errors = errors
        self.tell = base.tell
        self.seek = base.seek
        self.close = base.close

    def write(self, chars):
        if isinstance(chars, str):
            chars = unicode(chars) # Fail if it's not ASCII
        self.base.write(chars.encode(self.encoding, self.errors))
