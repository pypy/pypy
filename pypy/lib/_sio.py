"""New standard I/O library.

Based on sio.py from Guido van Rossum.

- This module contains various stream classes which provide a subset of the
  classic Python I/O API: read(n), write(s), tell(), seek(offset, whence=0),
  readall(), readline(), truncate(size), flush(), close().

- This is not for general usage:
  * read(n) may return less than n bytes, just like os.read().
  * some other methods also have no default parameters.
  * close() should be called exactly once and no further operations performed;
    there is no __del__() closing the stream for you.
  * some methods may raise NotImplementedError.

- A 'basis stream' provides I/O using a low-level API, like the os, mmap or
  socket modules.

- A 'filtering stream' builds on top of another stream.  There are filtering
  streams for universal newline translation, for unicode translation, and
  for buffering.

You typically take a basis stream, place zero or more filtering
streams on top of it, and then top it off with an input-buffering and/or
an outout-buffering stream.

"""

import os

# ____________________________________________________________


class Stream(object):

    """Base class for streams.  Provides a default implementation of
    some methods."""

    def read(self, n):
        raise NotImplementedError

    def write(self, data):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def seek(self, offset, whence=0):
        raise NotImplementedError

    def readall(self):
        bufsize = 8192
        result = []
        while True:
            data = self.read(bufsize)
            if not data:
                break
            result.append(data)
            if bufsize < 4194304:    # 4 Megs
                bufsize <<= 1
        return ''.join(result)

    def readline(self):
        # very inefficient
        result = []
        c = self.read(1)
        while c:
            result.append(c)
            if c == '\n':
                break
            c = self.read(1)
        return ''.join(result)

    def truncate(self, size):
        raise NotImplementedError

    def flush(self):
        pass

    def close(self):
        pass


class DiskFile(Stream):

    """Standard I/O basis stream using os.open/close/read/write/lseek"""

    def __init__(self, fd):
        self.fd = fd

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
        os.close(self.fd)

    def truncate(self, size):
        try:
            os.ftruncate(self.fd, size)
        except AttributeError:
            raise NotImplementedError


class MMapFile(Stream):

    """Standard I/O basis stream using mmap."""

##    def __init__(self, filename, mode="r"):
##        import mmap
##        self.filename = filename
##        self.mode = mode
##        if mode == "r":
##            flag = os.O_RDONLY
##            self.access = mmap.ACCESS_READ
##        else:
##            if mode == "w":
##                flag = os.O_RDWR | os.O_CREAT
##            elif mode == "a":
##                flag = os.O_RDWR
##            else:
##                raise ValueError, "mode should be 'r', 'w' or 'a'"
##            self.access = mmap.ACCESS_WRITE
##        if hasattr(os, "O_BINARY"):
##            flag |= os.O_BINARY
##        self.fd = os.open(filename, flag)
##        try:
##            self.mapfile()
##        except:
##            os.close(self.fd)
##            raise
##        self.pos = 0

    def __init__(self, fd, mmapaccess):
        self.fd = fd
        self.access = mmapaccess
        self.pos = 0
        self.remapfile()

    def remapfile(self):
        import mmap
        size = os.fstat(self.fd).st_size
        self.mm = mmap.mmap(self.fd, size, access=self.access)

    def close(self):
        self.mm.close()
        os.close(self.fd)

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
        filesize = self.mm.size() # Actual file size, may be more than mapped
        n = filesize - self.pos
        data = self.mm[self.pos:]
        if len(data) < n:
            del data
            # File grew since opened; remap to get the new data
            self.remapfile()
            data = self.mm[self.pos:]
        self.pos += len(data)
        return data

    def read(self, n):
        end = self.pos + n
        data = self.mm[self.pos:end]
        if not data:
            # is there more data to read?
            filesize = self.mm.size() #Actual file size, may be more than mapped
            if filesize > self.pos:
                # File grew since opened; remap to get the new data
                self.remapfile()
                data = self.mm[self.pos:end]
        self.pos += len(data)
        return data

    def readline(self):
        hit = self.mm.find("\n", self.pos) + 1
        if not hit:
            # is there more data to read?
            filesize = self.mm.size() # Actual file size, may be more than mapped
            if filesize <= len(self.mm):
                return ""
            # File grew since opened; remap to get the new data
            self.remapfile()
            hit = self.mm.find("\n", self.pos) + 1
        if hit:
            # Got a whole line
            data = self.mm[self.pos:hit]
            self.pos = hit
        else:
            # Read whatever we've got -- may be empty
            data = self.mm[self.pos:]
            self.pos += len(data)
        return data

    def write(self, data):
        end = self.pos + len(data)
        try:
            self.mm[self.pos:end] = data
            # This can raise IndexError on Windows, ValueError on Unix
        except (IndexError, ValueError):
            # XXX On Unix, this resize() call doesn't work
            self.mm.resize(end)
            self.mm[self.pos:end] = data
        self.pos = end

    def flush(self):
        self.mm.flush()

# ____________________________________________________________


def PassThrough(meth_name, flush_buffers):
    if flush_buffers:
        code = """def %s(self, *args):
                      self.flush_buffers()
                      return self.base.%s(*args)
"""
    else:
        code = """def %s(self, *args):
                      return self.base.%s(*args)
"""
    d = {}
    exec code % (meth_name, meth_name) in d
    return d[meth_name]


class BufferingInputStream(Stream):

    """Standard buffering input stream.

    This, and BufferingOutputStream if needed, are typically at the top of
    the stack of streams.
    """

    bigsize = 2**19 # Half a Meg
    bufsize = 2**13 # 8 K

    def __init__(self, base, bufsize=None):
        self.base = base
        self.do_read = base.read   # function to fill buffer some more
        self.do_tell = base.tell   # return a byte offset
        self.do_seek = base.seek   # seek to a byte offset
        if bufsize is None:     # Get default from the class
            bufsize = self.bufsize
        self.bufsize = bufsize  # buffer size (hint only)
        self.lines = []         # ready-made lines (sans "\n")
        self.buf = ""           # raw data (may contain "\n")
        # Invariant: readahead == "\n".join(self.lines + [self.buf])
        # self.lines contains no "\n"
        # self.buf may contain "\n"

    def flush_buffers(self):
        if self.lines or self.buf:
            try:
                self.do_seek(self.tell())
            except NotImplementedError:
                pass
            else:
                self.lines = []
                self.buf = ""

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
        if whence == 0:
            self.do_seek(offset, 0)
            self.lines = []
            self.buf = ""
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
            try:
                self.do_seek(offset, 1)
            except NotImplementedError:
                self.read(offset)
            return
        if whence == 2:
            try:
                self.do_seek(offset, 2)
            except NotImplementedError:
                pass
            else:
                self.lines = []
                self.buf = ""
                return
            # Skip relative to EOF by reading and saving only just as
            # much as needed
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

    def read(self, n):
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

    def readline(self):
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

        return "".join(buf)

    write      = PassThrough("write",     flush_buffers=True)
    truncate   = PassThrough("truncate",  flush_buffers=True)
    flush      = PassThrough("flush",     flush_buffers=True)
    close      = PassThrough("close",     flush_buffers=False)


class BufferingOutputStream(Stream):

    """Standard buffering output stream.

    This, and BufferingInputStream if needed, are typically at the top of
    the stack of streams.
    """

    bigsize = 2**19 # Half a Meg
    bufsize = 2**13 # 8 K

    def __init__(self, base, bufsize=None):
        self.base = base
        self.do_write = base.write  # write more data
        self.do_tell  = base.tell   # return a byte offset
        if bufsize is None:     # Get default from the class
            bufsize = self.bufsize
        self.bufsize = bufsize  # buffer size (hint only)
        self.buf = ""

    def flush_buffers(self):
        if self.buf:
            self.do_write(self.buf)
            self.buf = ""

    def tell(self):
        return self.do_tell() + len(self.buf)

    def write(self, data):
        buflen = len(self.buf)
        datalen = len(data)
        if datalen + buflen <= self.bufsize:
            self.buf += data
        elif buflen:
            self.buf += data[:self.bufsize-buflen]
            self.do_write(self.buf)
            self.buf = ""
            self.write(data[self.bufsize-buflen:])
        else:
            self.do_write(data)

    read       = PassThrough("read",     flush_buffers=True)
    readall    = PassThrough("readall",  flush_buffers=True)
    readline   = PassThrough("readline", flush_buffers=True)
    seek       = PassThrough("seek",     flush_buffers=True)
    truncate   = PassThrough("truncate", flush_buffers=True)
    flush      = PassThrough("flush",    flush_buffers=True)
    close      = PassThrough("close",    flush_buffers=True)


class LineBufferingOutputStream(BufferingOutputStream):

    """Line buffering output stream.

    This is typically the top of the stack.
    """

    def write(self, data):
        super(LineBufferingOutputStream, self).write(data)
        p = self.buf.rfind('\n') + 1
        if p:
            self.do_write(self.buf[:p])
            self.buf = self.buf[p:]

# ____________________________________________________________


class CRLFFilter(Stream):

    """Filtering stream for universal newlines.

    TextInputFilter is more general, but this is faster when you don't
    need tell/seek.
    """

    def __init__(self, base):
        self.base = base
        self.do_read = base.read
        self.atcr = False

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

    flush    = PassThrough("flush", flush_buffers=False)
    close    = PassThrough("close", flush_buffers=False)


class TextInputFilter(Stream):

    """Filtering input stream for universal newline translation."""

    def __init__(self, base):
        self.base = base   # must implement read, may implement tell, seek
        self.do_read = base.read
        self.atcr = False  # Set when last char read was \r
        self.buf = ""      # Optional one-character read-ahead buffer
        self.CR = False
        self.NL = False
        self.CRLF = False

    def getnewlines(self):
        foundchars = self.CR * 1 + self.NL * 2 + self.CRLF * 4
        if not foundchars:
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
        if self.buf:
            assert not self.atcr
            data = self.buf
            self.buf = ""
            return data
        data = self.do_read(n)

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
                    data = self.do_read(n)
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
            self.buf = self.do_read(1)
            pos += 1
            self.atcr = False
            if self.buf == "\n":
                self.buf = ""
        return pos - len(self.buf)

    def flush_buffers(self):
        if self.atcr:
            assert not self.buf
            self.buf = self.do_read(1)
            self.atcr = False
            if self.buf == "\n":
                self.buf = ""
        if self.buf:
            try:
                self.do_seek(-len(self.buf), 1)
            except NotImplementedError:
                pass
            else:
                self.buf = ""

    write      = PassThrough("write",     flush_buffers=True)
    truncate   = PassThrough("truncate",  flush_buffers=True)
    flush      = PassThrough("flush",     flush_buffers=True)
    close      = PassThrough("close",     flush_buffers=False)


class TextOutputFilter(Stream):

    """Filtering output stream for universal newline translation."""

    def __init__(self, base, linesep=os.linesep):
        assert linesep in ["\n", "\r\n", "\r"]
        self.base = base    # must implement write, may implement seek, tell
        self.linesep = linesep

    def write(self, data):
        data = data.replace("\n", self.linesep)
        self.base.write(data)

    tell       = PassThrough("tell",      flush_buffers=False)
    seek       = PassThrough("seek",      flush_buffers=False)
    read       = PassThrough("read",      flush_buffers=False)
    readall    = PassThrough("readall",   flush_buffers=False)
    readline   = PassThrough("readline",  flush_buffers=False)
    truncate   = PassThrough("truncate",  flush_buffers=False)
    flush      = PassThrough("flush",     flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)


class DecodingInputFilter(Stream):

    """Filtering input stream that decodes an encoded file."""

    def __init__(self, base, encoding="utf8", errors="strict"):
        self.base = base
        self.do_read = base.read
        self.encoding = encoding
        self.errors = errors

    def read(self, n):
        """Read *approximately* n bytes, then decode them.

        Under extreme circumstances,
        the return length could be longer than n!

        Always return a unicode string.

        This does *not* translate newlines;
        you can stack TextInputFilter.
        """
        data = self.do_read(n)
        try:
            return data.decode(self.encoding, self.errors)
        except ValueError:
            # XXX Sigh.  decode() doesn't handle incomplete strings well.
            # Use the retry strategy from codecs.StreamReader.
            for i in range(9):
                more = self.do_read(1)
                if not more:
                    raise
                data += more
                try:
                    return data.decode(self.encoding, self.errors)
                except ValueError:
                    pass
            raise

    write      = PassThrough("write",     flush_buffers=False)
    truncate   = PassThrough("truncate",  flush_buffers=False)
    flush      = PassThrough("flush",     flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)


class EncodingOutputFilter(Stream):

    """Filtering output stream that writes to an encoded file."""

    def __init__(self, base, encoding="utf8", errors="strict"):
        self.base = base
        self.do_write = base.write
        self.encoding = encoding
        self.errors = errors

    def write(self, chars):
        if isinstance(chars, str):
            chars = unicode(chars) # Fail if it's not ASCII
        self.do_write(chars.encode(self.encoding, self.errors))

    tell       = PassThrough("tell",      flush_buffers=False)
    seek       = PassThrough("seek",      flush_buffers=False)
    read       = PassThrough("read",      flush_buffers=False)
    readall    = PassThrough("readall",   flush_buffers=False)
    readline   = PassThrough("readline",  flush_buffers=False)
    truncate   = PassThrough("truncate",  flush_buffers=False)
    flush      = PassThrough("flush",     flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
