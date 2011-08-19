"""New standard I/O library.

Based on sio.py from Guido van Rossum.

- This module contains various stream classes which provide a subset of the
  classic Python I/O API: read(n), write(s), tell(), seek(offset, whence=0),
  readall(), readline(), truncate(size), flush(), close(), peek(),
  flushable(), try_to_find_file_descriptor().

- This is not for general usage:
  * read(n) may return less than n bytes, just like os.read().
  * some other methods also have no default parameters.
  * close() should be called exactly once and no further operations performed;
    there is no __del__() closing the stream for you.
  * some methods may raise MyNotImplementedError.
  * peek() returns some (or no) characters that have already been read ahead.
  * flushable() returns True/False if flushing that stream is useful/pointless.

- A 'basis stream' provides I/O using a low-level API, like the os, mmap or
  socket modules.

- A 'filtering stream' builds on top of another stream.  There are filtering
  streams for universal newline translation, for unicode translation, and
  for buffering.

You typically take a basis stream, place zero or more filtering
streams on top of it, and then top it off with an input-buffering and/or
an outout-buffering stream.

"""

#
# File offsets are all 'r_longlong', but a single read or write cannot
# transfer more data that fits in an RPython 'int' (because that would not
# fit in a single string anyway).  This module needs to be careful about
# where r_longlong values end up: as argument to seek() and truncate() and
# return value of tell(), but not as argument to read().
#

import os, sys
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rlib.rarithmetic import r_longlong, intmask
from pypy.rlib import rposix

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

class MyNotImplementedError(Exception):
    """
    Catching NotImplementedError is not RPython, so we use this custom class
    instead of it
    """

# ____________________________________________________________


def replace_crlf_with_lf(s):
    substrings = s.split("\r")
    result = [substrings[0]]
    for substring in substrings[1:]:
        if not substring:
            result.append("")
        elif substring[0] == "\n":
            result.append(substring[1:])
        else:
            result.append(substring)
    return "\n".join(result)

def replace_char_with_str(string, c, s):
    return s.join(string.split(c))


@specialize.argtype(0)
def open_file_as_stream(path, mode="r", buffering=-1):
    os_flags, universal, reading, writing, basemode, binary = decode_mode(mode)
    stream = open_path_helper(path, os_flags, basemode == "a")
    return construct_stream_tower(stream, buffering, universal, reading,
                                  writing, binary)

def _setfd_binary(fd):
    pass
    
def fdopen_as_stream(fd, mode, buffering=-1):
    # XXX XXX XXX you want do check whether the modes are compatible
    # otherwise you get funny results
    os_flags, universal, reading, writing, basemode, binary = decode_mode(mode)
    _setfd_binary(fd)
    stream = DiskFile(fd)
    return construct_stream_tower(stream, buffering, universal, reading,
                                  writing, binary)

@specialize.argtype(0)
def open_path_helper(path, os_flags, append):
    # XXX for now always return DiskFile
    fd = rposix.open(path, os_flags, 0666)
    if append:
        try:
            os.lseek(fd, 0, 2)
        except OSError:
            # XXX does this pass make sense?
            pass
    return DiskFile(fd)

def decode_mode(mode):
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
    flag |= O_BINARY

    reading = basemode == 'r' or plus
    writing = basemode != 'r' or plus

    return flag, universal, reading, writing, basemode, binary


def construct_stream_tower(stream, buffering, universal, reading, writing,
                           binary):
    if buffering == 0:   # no buffering
        if reading:      # force some minimal buffering for readline()
            stream = ReadlineInputStream(stream)
    elif buffering == 1:   # line-buffering
        if writing:
            stream = LineBufferingOutputStream(stream)
        if reading:
            stream = BufferingInputStream(stream)

    else:     # default or explicit buffer sizes
        if buffering is not None and buffering < 0:
            buffering = -1
        if writing:
            stream = BufferingOutputStream(stream, buffering)
        if reading:
            stream = BufferingInputStream(stream, buffering)

    if universal:     # Wants universal newlines
        if writing and os.linesep != '\n':
            stream = TextOutputFilter(stream)
        if reading:
            stream = TextInputFilter(stream)
    elif not binary and os.linesep == '\r\n':
        stream = TextCRLFFilter(stream)
    return stream


class StreamError(Exception):
    def __init__(self, message):
        self.message = message

StreamErrors = (OSError, StreamError)     # errors that can generally be raised


if sys.platform == "win32":
    from pypy.rlib import rwin32
    from pypy.translator.tool.cbuild import ExternalCompilationInfo
    from pypy.rpython.lltypesystem import rffi
    import errno

    _eci = ExternalCompilationInfo()
    _get_osfhandle = rffi.llexternal('_get_osfhandle', [rffi.INT], rffi.LONG,
                                     compilation_info=_eci)
    _setmode = rffi.llexternal('_setmode', [rffi.INT, rffi.INT], rffi.INT,
                               compilation_info=_eci)
    SetEndOfFile = rffi.llexternal('SetEndOfFile', [rffi.LONG], rwin32.BOOL,
                                   compilation_info=_eci)

    # HACK: These implementations are specific to MSVCRT and the C backend.
    # When generating on CLI or JVM, these are patched out.
    # See PyPyTarget.target() in targetpypystandalone.py
    def _setfd_binary(fd):
        _setmode(fd, os.O_BINARY)

    def ftruncate_win32(fd, size):
        curpos = os.lseek(fd, 0, 1)
        try:
            # move to the position to be truncated
            os.lseek(fd, size, 0)
            # Truncate.  Note that this may grow the file!
            handle = _get_osfhandle(fd)
            if handle == -1:
                raise OSError(errno.EBADF, "Invalid file handle")
            if not SetEndOfFile(handle):
                raise WindowsError(rwin32.GetLastError(),
                                   "Could not truncate file")
        finally:
            # we restore the file pointer position in any case
            os.lseek(fd, curpos, 0)


class Stream(object):

    """Base class for streams.  Provides a default implementation of
    some methods."""

    def read(self, n):
        raise MyNotImplementedError

    def write(self, data):
        raise MyNotImplementedError

    def tell(self):
        raise MyNotImplementedError

    def seek(self, offset, whence):
        raise MyNotImplementedError

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
        # very inefficient unless there is a peek()
        result = []
        while True:
            # "peeks" on the underlying stream to see how many characters
            # we can safely read without reading past an end-of-line
            peeked = self.peek()
            pn = peeked.find("\n")
            if pn < 0:
                pn = len(peeked)
            c = self.read(pn + 1)
            if not c:
                break
            result.append(c)
            if c.endswith('\n'):
                break
        return ''.join(result)

    def truncate(self, size):
        raise MyNotImplementedError

    def flush_buffers(self):
        pass

    def flush(self):
        pass

    def flushable(self):
        return False

    def close(self):
        pass

    def peek(self):
        return ''

    def try_to_find_file_descriptor(self):
        return -1

    def getnewlines(self):
        return 0


class DiskFile(Stream):

    """Standard I/O basis stream using os.open/close/read/write/lseek"""

    def __init__(self, fd):
        self.fd = fd

    def seek(self, offset, whence):
        os.lseek(self.fd, offset, whence)

    def tell(self):
        return os.lseek(self.fd, 0, 1)

    def read(self, n):
        assert isinstance(n, int)
        return os.read(self.fd, n)

    def write(self, data):
        while data:
            n = os.write(self.fd, data)
            data = data[n:]

    def close(self):
        os.close(self.fd)

    if sys.platform == "win32":
        def truncate(self, size):
            ftruncate_win32(self.fd, size)
    else:
        def truncate(self, size):
            # Note: for consistency, in translated programs a failing
            # os.ftruncate() raises OSError.  However, on top of
            # CPython, we get an IOError.  As it is (as far as I know)
            # the only place that have this behavior, we just convert it
            # to an OSError instead of adding IOError to StreamErrors.
            if we_are_translated():
                os.ftruncate(self.fd, size)
            else:
                try:
                    os.ftruncate(self.fd, size)
                except IOError, e:
                    raise OSError(*e.args)

    def try_to_find_file_descriptor(self):
        return self.fd

# next class is not RPython

class MMapFile(Stream):

    """Standard I/O basis stream using mmap."""

    def __init__(self, fd, mmapaccess):
        """NOT_RPYTHON"""
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

    def seek(self, offset, whence):
        if whence == 0:
            self.pos = max(0, offset)
        elif whence == 1:
            self.pos = max(0, self.pos + offset)
        elif whence == 2:
            self.pos = max(0, self.mm.size() + offset)
        else:
            raise StreamError("seek(): whence must be 0, 1 or 2")

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
        assert isinstance(n, int)
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
            filesize = self.mm.size() #Actual file size, may be more than mapped
            if filesize > len(self.mm):
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

    def flushable(self):
        import mmap
        return self.access == mmap.ACCESS_WRITE

    def try_to_find_file_descriptor(self):
        return self.fd

# ____________________________________________________________

STREAM_METHODS = dict([
    ("read", [int]),
    ("write", [str]),
    ("tell", []),
    ("seek", [r_longlong, int]),
    ("readall", []),
    ("readline", []),
    ("truncate", [r_longlong]),
    ("flush", []),
    ("flushable", []),
    ("close", []),
    ("peek", []),
    ("try_to_find_file_descriptor", []),
    ("getnewlines", []),
    ])

def PassThrough(meth_name, flush_buffers):
    if meth_name in STREAM_METHODS:
        signature = STREAM_METHODS[meth_name]
        args = ", ".join(["v%s" % (i, ) for i in range(len(signature))])
    else:
        assert 0, "not a good idea"
        args = "*args"
    if flush_buffers:
        code = """def %s(self, %s):
                      self.flush_buffers()
                      return self.base.%s(%s)
"""
    else:
        code = """def %s(self, %s):
                      return self.base.%s(%s)
"""
    d = {}
    exec code % (meth_name, args, meth_name, args) in d
    return d[meth_name]


def offset2int(offset):
    intoffset = intmask(offset)
    if intoffset != offset:
        raise StreamError("seek() from a non-seekable source:"
                          " this would read and discard more"
                          " than sys.maxint bytes")
    return intoffset

class BufferingInputStream(Stream):

    """Standard buffering input stream.

    This, and BufferingOutputStream if needed, are typically at the top of
    the stack of streams.
    """

    bigsize = 2**19 # Half a Meg
    bufsize = 2**13 # 8 K

    def __init__(self, base, bufsize=-1):
        self.base = base
        self.do_read = base.read   # function to fill buffer some more
        self.do_tell = base.tell   # return a byte offset
        self.do_seek = base.seek   # seek to a byte offset
        if bufsize == -1:     # Get default from the class
            bufsize = self.bufsize
        self.bufsize = bufsize  # buffer size (hint only)
        self.buf = ""           # raw data
        self.pos = 0

    def flush_buffers(self):
        if self.buf:
            try:
                self.do_seek(self.tell(), 0)
            except MyNotImplementedError:
                pass
            else:
                self.buf = ""
                self.pos = 0

    def tell(self):
        tellpos = self.do_tell()  # This may fail
        offset = len(self.buf) - self.pos
        assert tellpos >= offset #, (locals(), self.__dict__)
        return tellpos - offset

    def seek(self, offset, whence):
        # This may fail on the do_seek() or do_tell() call.
        # But it won't call either on a relative forward seek.
        # Nor on a seek to the very end.
        if whence == 0:
            self.do_seek(offset, 0)
            self.buf = ""
            self.pos = 0
            return
        if whence == 1:
            currentsize = len(self.buf) - self.pos
            if offset < 0:
                if self.pos + offset >= 0:
                    self.pos += offset
                else:
                    self.do_seek(self.tell() + offset, 0)
                    self.pos = 0
                    self.buf = ""
                return
            elif offset <= currentsize:
                self.pos += offset
                return
            self.buf = ""
            self.pos = 0
            offset -= currentsize
            try:
                self.do_seek(offset, 1)
            except MyNotImplementedError:
                intoffset = offset2int(offset)
                self.read(intoffset)
            return
        if whence == 2:
            self.do_seek(offset, 2)
            self.pos = 0
            self.buf = ""
            return
            # We'll comment all of this for now unless someone really wants
            # something like it
            #try:
            #    self.do_seek(offset, 2)
            #except MyNotImplementedError:
            #    pass
            #else:
            #    self.pos = 0
            #    self.buf = ""
            #    return
            # Skip relative to EOF by reading and saving only just as
            # much as needed
            #intoffset = offset2int(offset)
            #self.lines.reverse()
            #data = "\n".join(self.lines + [self.buf])
            #total = len(data)
            #buffers = [data]
            #self.lines = []
            #self.buf = ""
            #while 1:
                #data = self.do_read(self.bufsize)
                #if not data:
                    #break
                #buffers.append(data)
                #total += len(data)
                #while buffers and total >= len(buffers[0]) - intoffset:
                    #total -= len(buffers[0])
                    #del buffers[0]
            #cutoff = total + intoffset
            #if cutoff < 0:
                #raise StreamError("cannot seek back")
            #if buffers:
                #buffers[0] = buffers[0][cutoff:]
            #self.buf = "".join(buffers)
            #self.lines = []
            #return
        raise StreamError("whence should be 0, 1 or 2")

    def readall(self):
        pos = self.pos
        assert pos >= 0
        chunks = [self.buf[pos:]]
        self.buf = ""
        self.pos = 0
        bufsize = self.bufsize
        while 1:
            data = self.do_read(bufsize)
            if not data:
                break
            chunks.append(data)
            bufsize = min(bufsize*2, self.bigsize)
        return "".join(chunks)

    def read(self, n=-1):
        assert isinstance(n, int)
        if n < 0:
            return self.readall()
        currentsize = len(self.buf) - self.pos
        start = self.pos
        assert start >= 0
        if n <= currentsize:
            stop = start + n
            assert stop >= 0
            result = self.buf[start:stop]
            self.pos += n
            return result
        else:
            chunks = [self.buf[start:]]
            while 1:
                self.buf = self.do_read(self.bufsize)
                if not self.buf:
                    self.pos = 0
                    break
                currentsize += len(self.buf)
                if currentsize >= n:
                    self.pos = len(self.buf) - (currentsize - n)
                    stop = self.pos
                    assert stop >= 0
                    chunks.append(self.buf[:stop])
                    break
                chunks.append(self.buf)
            return ''.join(chunks)

    def readline(self):
        pos = self.pos
        assert pos >= 0
        i = self.buf.find("\n", pos)
        start = self.pos
        assert start >= 0
        if i >= 0: # new line found
            i += 1
            result = self.buf[start:i]
            self.pos = i
            return result
        temp = self.buf[start:]
        # read one buffer and most of the time a new line will be found
        self.buf = self.do_read(self.bufsize)
        i = self.buf.find("\n")
        if i >= 0: # new line found
            i += 1
            result = temp + self.buf[:i]
            self.pos = i
            return result
        if not self.buf:
            self.pos = 0
            return temp
        # need to keep getting data until we find a new line
        chunks = [temp, self.buf]
        while 1:
            self.buf = self.do_read(self.bufsize)
            if not self.buf:
                self.pos = 0
                break
            i = self.buf.find("\n")
            if i >= 0:
                i += 1
                chunks.append(self.buf[:i])
                self.pos = i
                break
            chunks.append(self.buf)
        return "".join(chunks)

    def peek(self):
        pos = self.pos
        assert pos >= 0
        return self.buf[pos:]

    write      = PassThrough("write",     flush_buffers=True)
    truncate   = PassThrough("truncate",  flush_buffers=True)
    flush      = PassThrough("flush",     flush_buffers=True)
    flushable  = PassThrough("flushable", flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)


class ReadlineInputStream(Stream):

    """Minimal buffering input stream.

    Only does buffering for readline().  The other kinds of reads, and
    all writes, are not buffered at all.
    """

    bufsize = 2**13 # 8 K

    def __init__(self, base, bufsize=-1):
        self.base = base
        self.do_read = base.read   # function to fill buffer some more
        self.do_seek = base.seek   # seek to a byte offset
        if bufsize == -1:     # Get default from the class
            bufsize = self.bufsize
        self.bufsize = bufsize  # buffer size (hint only)
        self.buf = None         # raw data (may contain "\n")
        self.bufstart = 0

    def flush_buffers(self):
        if self.buf is not None:
            try:
                self.do_seek(self.bufstart-len(self.buf), 1)
            except MyNotImplementedError:
                pass
            else:
                self.buf = None
                self.bufstart = 0

    def readline(self):
        if self.buf is not None:
            i = self.buf.find('\n', self.bufstart)
        else:
            self.buf = ''
            i = -1
        #
        if i < 0:
            self.buf = self.buf[self.bufstart:]
            self.bufstart = 0
            while True:
                bufsize = max(self.bufsize, len(self.buf) >> 2)
                data = self.do_read(bufsize)
                if not data:
                    result = self.buf              # end-of-file reached
                    self.buf = None
                    return result
                startsearch = len(self.buf)   # there is no '\n' in buf so far
                self.buf += data
                i = self.buf.find('\n', startsearch)
                if i >= 0:
                    break
        #
        i += 1
        result = self.buf[self.bufstart:i]
        self.bufstart = i
        return result

    def peek(self):
        if self.buf is None:
            return ''
        if self.bufstart > 0:
            self.buf = self.buf[self.bufstart:]
            self.bufstart = 0
        return self.buf

    def tell(self):
        pos = self.base.tell()
        if self.buf is not None:
            pos -= (len(self.buf) - self.bufstart)
        return pos

    def readall(self):
        result = self.base.readall()
        if self.buf is not None:
            result = self.buf[self.bufstart:] + result
            self.buf = None
            self.bufstart = 0
        return result

    def read(self, n):
        if self.buf is None:
            return self.do_read(n)
        else:
            m = n - (len(self.buf) - self.bufstart)
            start = self.bufstart
            if m > 0:
                result = self.buf[start:] + self.do_read(m)
                self.buf = None
                self.bufstart = 0
                return result
            elif n >= 0:
                self.bufstart = start + n
                return self.buf[start : self.bufstart]
            else:
                return ''

    seek       = PassThrough("seek",      flush_buffers=True)
    write      = PassThrough("write",     flush_buffers=True)
    truncate   = PassThrough("truncate",  flush_buffers=True)
    flush      = PassThrough("flush",     flush_buffers=True)
    flushable  = PassThrough("flushable", flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)


class BufferingOutputStream(Stream):

    """Standard buffering output stream.

    This, and BufferingInputStream if needed, are typically at the top of
    the stack of streams.
    """

    bigsize = 2**19 # Half a Meg
    bufsize = 2**13 # 8 K

    def __init__(self, base, bufsize=-1):
        self.base = base
        self.do_write = base.write  # write more data
        self.do_tell  = base.tell   # return a byte offset
        if bufsize == -1:     # Get default from the class
            bufsize = self.bufsize
        self.bufsize = bufsize  # buffer size (hint only)
        self.buf = []
        self.buflen = 0

    def flush_buffers(self):
        if self.buf:
            self.do_write(''.join(self.buf))
            self.buf = []
            self.buflen = 0

    def tell(self):
        return self.do_tell() + self.buflen

    def write(self, data):
        buflen = self.buflen
        datalen = len(data)
        if datalen + buflen < self.bufsize:
            self.buf.append(data)
            self.buflen += datalen
        elif buflen:
            self.buf.append(data)
            self.do_write(''.join(self.buf))
            self.buf = []
            self.buflen = 0
        else:
            self.do_write(data)

    read       = PassThrough("read",     flush_buffers=True)
    readall    = PassThrough("readall",  flush_buffers=True)
    readline   = PassThrough("readline", flush_buffers=True)
    seek       = PassThrough("seek",     flush_buffers=True)
    truncate   = PassThrough("truncate", flush_buffers=True)
    flush      = PassThrough("flush",    flush_buffers=True)
    close      = PassThrough("close",    flush_buffers=True)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)

    def flushable(self):
        return True


class LineBufferingOutputStream(BufferingOutputStream):

    """Line buffering output stream.

    This is typically the top of the stack.
    """

    def write(self, data):
        p = data.rfind('\n') + 1
        assert p >= 0
        if self.buflen + len(data) < self.bufsize:
            if p == 0:
                self.buf.append(data)
                self.buflen += len(data)
            else:
                if self.buflen:
                    self.do_write(''.join(self.buf))
                self.do_write(data[:p])
                self.buf = [data[p:]]
                self.buflen = len(self.buf[0])
        else:
            if self.buflen + p < self.bufsize:
                p = self.bufsize - self.buflen
            if self.buflen:
                self.do_write(''.join(self.buf))
            assert p >= 0
            self.do_write(data[:p])
            self.buf = [data[p:]]
            self.buflen = len(self.buf[0])


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
            data = replace_crlf_with_lf(data)
        return data

    flush    = PassThrough("flush", flush_buffers=False)
    flushable= PassThrough("flushable", flush_buffers=False)
    close    = PassThrough("close", flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)

class TextCRLFFilter(Stream):

    """Filtering stream for universal newlines.

    TextInputFilter is more general, but this is faster when you don't
    need tell/seek.
    """

    def __init__(self, base):
        self.base = base
        self.do_read = base.read
        self.do_write = base.write
        self.do_flush = base.flush_buffers
        self.lfbuffer = ""

    def read(self, n):
        data = self.lfbuffer + self.do_read(n)
        self.lfbuffer = ""
        if data.endswith("\r"):
            c = self.do_read(1)
            if c and c[0] == '\n':
                data = data + '\n'
                self.lfbuffer = c[1:]
            else:
                self.lfbuffer = c

        result = []
        offset = 0
        while True:
            newoffset = data.find('\r\n', offset)
            if newoffset < 0:
                result.append(data[offset:])
                break
            result.append(data[offset:newoffset])
            offset = newoffset + 2

        return '\n'.join(result)

    def tell(self):
        pos = self.base.tell()
        return pos - len(self.lfbuffer)

    def seek(self, offset, whence):
        if whence == 1:
            offset -= len(self.lfbuffer)   # correct for already-read-ahead character
        self.base.seek(offset, whence)
        self.lfbuffer = ""

    def flush_buffers(self):
        if self.lfbuffer:
            self.base.seek(-len(self.lfbuffer), 1)
            self.lfbuffer = ""
        self.do_flush()

    def write(self, data):
        data = replace_char_with_str(data, '\n', '\r\n')
        self.flush_buffers()
        self.do_write(data)

    truncate = PassThrough("truncate", flush_buffers=True)
    flush    = PassThrough("flush", flush_buffers=False)
    flushable= PassThrough("flushable", flush_buffers=False)
    close    = PassThrough("close", flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)
    
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
        return self.CR * 1 + self.NL * 2 + self.CRLF * 4

    def read(self, n):
        """Read up to n bytes."""
        if self.buf:
            assert not self.atcr
            data = self.buf
            self.buf = ""
        else:
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
            data = replace_crlf_with_lf(data)
            
        return data

    def readline(self):
        result = []
        while True:
            # "peeks" on the underlying stream to see how many characters
            # we can safely read without reading past an end-of-line
            peeked = self.base.peek()
            pn = peeked.find("\n")
            pr = peeked.find("\r")
            if pn < 0: pn = len(peeked)
            if pr < 0: pr = len(peeked)
            c = self.read(min(pn, pr) + 1)
            if not c:
                break
            result.append(c)
            if c.endswith('\n'):
                break
        return ''.join(result)

    def seek(self, offset, whence):
        """Seeks based on knowledge that does not come from a tell()
           may go to the wrong place, since the number of
           characters seen may not match the number of characters
           that are actually in the file (where \r\n is the
           line separator). Arithmetics on the result
           of a tell() that moves beyond a newline character may in the
           same way give the wrong result.
        """
        if whence == 1:
            offset -= len(self.buf)   # correct for already-read-ahead character
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
                self.CRLF = True
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
                self.base.seek(-len(self.buf), 1)
            except MyNotImplementedError:
                pass
            else:
                self.buf = ""

    def peek(self):
        return self.buf

    write      = PassThrough("write",     flush_buffers=True)
    truncate   = PassThrough("truncate",  flush_buffers=True)
    flush      = PassThrough("flush",     flush_buffers=True)
    flushable  = PassThrough("flushable", flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)


class TextOutputFilter(Stream):

    """Filtering output stream for universal newline translation."""

    def __init__(self, base, linesep=os.linesep):
        assert linesep in ["\n", "\r\n", "\r"]
        self.base = base    # must implement write, may implement seek, tell
        self.linesep = linesep

    def write(self, data):
        data = replace_char_with_str(data, "\n", self.linesep)
        self.base.write(data)

    tell       = PassThrough("tell",      flush_buffers=False)
    seek       = PassThrough("seek",      flush_buffers=False)
    read       = PassThrough("read",      flush_buffers=False)
    readall    = PassThrough("readall",   flush_buffers=False)
    readline   = PassThrough("readline",  flush_buffers=False)
    truncate   = PassThrough("truncate",  flush_buffers=False)
    flush      = PassThrough("flush",     flush_buffers=False)
    flushable  = PassThrough("flushable", flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)


class CallbackReadFilter(Stream):
    """Pseudo read filter that invokes a callback before blocking on a read.
    """

    def __init__(self, base, callback):
        self.base = base
        self.callback = callback

    def flush_buffers(self):
        self.callback()

    tell       = PassThrough("tell",      flush_buffers=False)
    seek       = PassThrough("seek",      flush_buffers=False)
    read       = PassThrough("read",      flush_buffers=True)
    readall    = PassThrough("readall",   flush_buffers=True)
    readline   = PassThrough("readline",  flush_buffers=True)
    peek       = PassThrough("peek",      flush_buffers=False)
    flush      = PassThrough("flush",     flush_buffers=False)
    flushable  = PassThrough("flushable", flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
    write      = PassThrough("write",     flush_buffers=False)
    truncate   = PassThrough("truncate",  flush_buffers=False)
    getnewlines= PassThrough("getnewlines",flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)

# _________________________________________________
# The following functions are _not_ RPython!

class DecodingInputFilter(Stream):

    """Filtering input stream that decodes an encoded file."""

    def __init__(self, base, encoding="utf8", errors="strict"):
        """NOT_RPYTHON"""
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
    flushable  = PassThrough("flushable", flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)

class EncodingOutputFilter(Stream):

    """Filtering output stream that writes to an encoded file."""

    def __init__(self, base, encoding="utf8", errors="strict"):
        """NOT_RPYTHON"""
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
    flushable  = PassThrough("flushable", flush_buffers=False)
    close      = PassThrough("close",     flush_buffers=False)
    try_to_find_file_descriptor = PassThrough("try_to_find_file_descriptor",
                                              flush_buffers=False)
