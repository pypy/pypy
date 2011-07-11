from __future__ import with_statement
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, generic_new_descr, interp_attrproperty_w)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.buffer import RWBuffer
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.rarithmetic import r_longlong, intmask
from pypy.tool.sourcetools import func_renamer
from pypy.module._io.interp_iobase import (
    W_IOBase, DEFAULT_BUFFER_SIZE, convert_size,
    check_readable_w, check_writable_w, check_seekable_w)
from pypy.module._io.interp_io import W_BlockingIOError

STATE_ZERO, STATE_OK, STATE_DETACHED = range(3)

class BlockingIOError(Exception):
    pass

class W_BufferedIOBase(W_IOBase):
    def _unsupportedoperation(self, space, message):
        w_exc = space.getattr(space.getbuiltinmodule('_io'),
                              space.wrap('UnsupportedOperation'))
        raise OperationError(w_exc, space.wrap(message))

    def _check_init(self, space):
        raise NotImplementedError

    def _deprecated_max_buffer_size(self, space):
        space.warn("max_buffer_size is deprecated",
                   space.w_DeprecationWarning)

    def read_w(self, space, w_size=None):
        self._unsupportedoperation(space, "read")

    def read1_w(self, space, w_size):
        self._unsupportedoperation(space, "read1")

    def write_w(self, space, w_data):
        self._unsupportedoperation(space, "write")

    def detach_w(self, space):
        self._unsupportedoperation(space, "detach")

    def readinto_w(self, space, w_buffer):
        rwbuffer = space.rwbuffer_w(w_buffer)
        length = rwbuffer.getlength()
        w_data = space.call_method(self, "read", space.wrap(length))

        if not space.isinstance_w(w_data, space.w_str):
            raise OperationError(space.w_TypeError, space.wrap(
                "read() should return bytes"))
        data = space.str_w(w_data)
        rwbuffer.setslice(0, data)
        return space.wrap(len(data))

W_BufferedIOBase.typedef = TypeDef(
    '_io._BufferedIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_BufferedIOBase),
    read = interp2app(W_BufferedIOBase.read_w),
    read1 = interp2app(W_BufferedIOBase.read1_w),
    write = interp2app(W_BufferedIOBase.write_w),
    detach = interp2app(W_BufferedIOBase.detach_w),
    readinto = interp2app(W_BufferedIOBase.readinto_w),
)

class RawBuffer(RWBuffer):
    def __init__(self, buf, start, length):
        self.buf = buf
        self.start = start
        self.length = length

    def getlength(self):
        return self.length

    def setitem(self, index, char):
        self.buf[self.start + index] = char

class BufferedMixin:
    _mixin_ = True

    def __init__(self, space):
        W_IOBase.__init__(self, space)
        self.state = STATE_ZERO

        self.buffer = None

        self.abs_pos = 0    # Absolute position inside the raw stream (-1 if
                            # unknown).
        self.pos = 0        # Current logical position in the buffer
        self.raw_pos = 0    # Position of the raw stream in the buffer.

        self.read_end = -1  # Just after the last buffered byte in the buffer,
                            # or -1 if the buffer isn't ready for reading

        self.write_pos = 0  # Just after the last byte actually written
        self.write_end = -1 # Just after the last byte waiting to be written,
                            # or -1 if the buffer isn't ready for writing.

        self.lock = None

        self.readable = False
        self.writable = False

    def _reader_reset_buf(self):
        self.read_end = -1

    def _writer_reset_buf(self):
        self.write_pos = 0
        self.write_end = -1

    def _init(self, space):
        if self.buffer_size <= 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "buffer size must be strictly positive"))

        self.buffer = ['\0'] * self.buffer_size

        ## XXX cannot free a Lock?
        ## if self.lock:
        ##     self.lock.free()
        self.lock = space.allocate_lock()

        try:
            self._raw_tell(space)
        except OperationError:
            pass

    def _check_init(self, space):
        if self.state == STATE_ZERO:
            raise OperationError(space.w_ValueError, space.wrap(
                "I/O operation on uninitialized object"))
        elif self.state == STATE_DETACHED:
            raise OperationError(space.w_ValueError, space.wrap(
                "raw stream has been detached"))

    def _check_closed(self, space, message=None):
        self._check_init(space)
        W_IOBase._check_closed(self, space, message)

    def _raw_tell(self, space):
        w_pos = space.call_method(self.w_raw, "tell")
        pos = space.r_longlong_w(w_pos)
        if pos < 0:
            raise OperationError(space.w_IOError, space.wrap(
                "raw stream returned invalid position"))

        self.abs_pos = pos
        return pos

    def closed_get_w(self, space):
        self._check_init(space)
        return space.getattr(self.w_raw, space.wrap("closed"))

    def name_get_w(self, space):
        return space.getattr(self.w_raw, space.wrap("name"))

    def mode_get_w(self, space):
        return space.getattr(self.w_raw, space.wrap("mode"))

    def readable_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_raw, "readable")

    def writable_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_raw, "writable")

    def seekable_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_raw, "seekable")

    def isatty_w(self, space):
        return space.call_method(self.w_raw, "isatty")

    def repr_w(self, space):
        typename = space.type(self).getname(space)
        module = space.str_w(space.type(self).get_module())
        try:
            w_name = space.getattr(self, space.wrap("name"))
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            return space.wrap("<%s.%s>" % (module, typename,))
        else:
            name_repr = space.str_w(space.repr(w_name))
            return space.wrap("<%s.%s name=%s>" % (module, typename, name_repr))

    # ______________________________________________

    def _readahead(self):
        if self.readable and self.read_end != -1:
            available = self.read_end - self.pos
            assert available >= 0
            return available
        return 0

    def _raw_offset(self):
        if self.raw_pos >= 0 and (
            (self.readable and self.read_end != -1) or
            (self.writable and self.write_end != -1)):
            return self.raw_pos - self.pos
        return 0

    def tell_w(self, space):
        self._check_init(space)
        pos = self._raw_tell(space) - self._raw_offset()
        return space.wrap(pos)

    @unwrap_spec(pos=r_longlong, whence=int)
    def seek_w(self, space, pos, whence=0):
        self._check_init(space)
        if whence not in (0, 1, 2):
            raise operationerrfmt(space.w_ValueError,
                "whence must be between 0 and 2, not %d", whence)
        self._check_closed(space, "seek of closed file")
        if whence != 2 and self.readable:
            # Check if seeking leaves us inside the current buffer, so as to
            # return quickly if possible. Also, we needn't take the lock in
            # this fast path.
            if self.abs_pos == -1:
                self._raw_tell(space)
            current = self.abs_pos
            available = self._readahead()
            if available > 0:
                if whence == 0:
                    offset = pos - (current - self._raw_offset())
                else:
                    offset = pos
                if -self.pos <= offset <= available:
                    newpos = self.pos + offset
                    assert newpos >= 0
                    self.pos = newpos
                    return space.wrap(current - available + offset)

        # Fallback: invoke raw seek() method and clear buffer
        with self.lock:
            if self.writable:
                self._writer_flush_unlocked(space)
                self._writer_reset_buf()

            if whence == 1:
                pos -= self._raw_offset()
            n = self._raw_seek(space, pos, whence)
            self.raw_pos = -1
            if self.readable:
                self._reader_reset_buf()
            return space.wrap(n)

    def _raw_seek(self, space, pos, whence):
        w_pos = space.call_method(self.w_raw, "seek",
                                  space.wrap(pos), space.wrap(whence))
        pos = space.r_longlong_w(w_pos)
        if pos < 0:
            raise OperationError(space.w_IOError, space.wrap(
                "Raw stream returned invalid position"))
        return pos

    def _closed(self, space):
        return space.is_true(space.getattr(self.w_raw, space.wrap("closed")))

    def close_w(self, space):
        self._check_init(space)
        with self.lock:
            if self._closed(space):
                return
        space.call_method(self, "flush")
        with self.lock:
            space.call_method(self.w_raw, "close")

    def simple_flush_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_raw, "flush")

    def _writer_flush_unlocked(self, space, restore_pos=False):
        if self.write_end == -1 or self.write_pos == self.write_end:
            return
        # First, rewind
        rewind = self._raw_offset() + (self.pos - self.write_pos)
        if rewind != 0:
            self._raw_seek(space, -rewind, 1)
            self.raw_pos -= rewind

        written = 0
        while self.write_pos < self.write_end:
            try:
                n = self._raw_write(space, self.write_pos, self.write_end)
            except OperationError, e:
                if not e.match(space, space.gettypeobject(
                    W_BlockingIOError.typedef)):
                    raise
                w_exc = e.get_w_value(space)
                assert isinstance(w_exc, W_BlockingIOError)
                self.write_pos += w_exc.written
                self.raw_pos = self.write_pos
                written += w_exc.written
                # re-raise the error
                w_exc.written = written
                raise
            self.write_pos += n
            self.raw_pos = self.write_pos
            written += n
            # Partial writes can return successfully when interrupted by a
            # signal (see write(2)).  We must run signal handlers before
            # blocking another time, possibly indefinitely.
            space.getexecutioncontext().checksignals()

        if restore_pos:
            forward = rewind - written
            if forward:
                self._raw_seek(space, forward, 1)
                self.raw_pos += forward

        self._writer_reset_buf()

    def _write(self, space, data):
        w_data = space.wrap(data)
        w_written = space.call_method(self.w_raw, "write", w_data)
        written = space.getindex_w(w_written, space.w_IOError)
        if not 0 <= written <= len(data):
            raise OperationError(space.w_IOError, space.wrap(
                "raw write() returned invalid length"))
        if self.abs_pos != -1:
            self.abs_pos += written
        return written

    def _raw_write(self, space, start, end):
        # XXX inefficient
        l = []
        for i in range(start, end):
            l.append(self.buffer[i])
        return self._write(space, ''.join(l))

    def detach_w(self, space):
        self._check_init(space)
        space.call_method(self, "flush")
        w_raw = self.w_raw
        self.w_raw = None
        self.state = STATE_DETACHED
        return w_raw

    def fileno_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_raw, "fileno")

    def truncate_w(self, space, w_size=None):
        self._check_init(space)
        with self.lock:
            if self.writable:
                self._writer_flush_unlocked(space)
            if self.readable:
                if space.is_w(w_size, space.w_None):
                    # Rewind the raw stream so that its position corresponds
                    # to the current logical position
                    self._raw_seek(space, -self._raw_offset(), 1)
                self._reader_reset_buf()
            # invalidate cached position
            self.abs_pos = -1

            return space.call_method(self.w_raw, "truncate", w_size)

    # ________________________________________________________________
    # Read methods

    def read_w(self, space, w_size=None):
        self._check_init(space)
        self._check_closed(space, "read of closed file")
        size = convert_size(space, w_size)

        if size == -1:
            # read until the end of stream
            with self.lock:
                return self._read_all(space)
        elif size >= 0:
            res = self._read_fast(size)
            if res is None:
                with self.lock:
                    res = self._read_generic(space, size)
        else:
            raise OperationError(space.w_ValueError, space.wrap(
                "read length must be positive or -1"))
        return space.wrap(res)

    @unwrap_spec(size=int)
    def peek_w(self, space, size=0):
        self._check_init(space)
        with self.lock:
            if self.writable:
                self._writer_flush_unlocked(space, restore_pos=True)
            # Constraints:
            # 1. we don't want to advance the file position.
            # 2. we don't want to lose block alignment, so we can't shift the
            #    buffer to make some place.
            # Therefore, we either return `have` bytes (if > 0), or a full
            # buffer.
            have = self._readahead()
            if have > 0:
                data = ''.join(self.buffer[self.pos:self.pos+have])
                return space.wrap(data)

            # Fill the buffer from the raw stream, and copy it to the result
            self._reader_reset_buf()
            try:
                size = self._fill_buffer(space)
            except BlockingIOError:
                size = 0
            self.pos = 0
            data = ''.join(self.buffer[:size])
            return space.wrap(data)

    @unwrap_spec(size=int)
    def read1_w(self, space, size):
        self._check_init(space)
        self._check_closed(space, "read of closed file")

        if size < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "read length must be positive"))
        if size == 0:
            return space.wrap("")

        with self.lock:
            if self.writable:
                self._writer_flush_unlocked(space, restore_pos=True)

            # Return up to n bytes.  If at least one byte is buffered, we only
            # return buffered bytes.  Otherwise, we do one raw read.

            # XXX: this mimicks the io.py implementation but is probably
            # wrong. If we need to read from the raw stream, then we could
            # actually read all `n` bytes asked by the caller (and possibly
            # more, so as to fill our buffer for the next reads).

            have = self._readahead()
            if have == 0:
                # Fill the buffer from the raw stream
                self._reader_reset_buf()
                self.pos = 0
                try:
                    have = self._fill_buffer(space)
                except BlockingIOError:
                    have = 0
            if size > have:
                size = have
            endpos = self.pos + size
            data = ''.join(self.buffer[self.pos:endpos])
            self.pos = endpos
            return space.wrap(data)

    def _read_all(self, space):
        "Read all the file, don't update the cache"
        builder = StringBuilder()
        # First copy what we have in the current buffer
        current_size = self._readahead()
        data = None
        if current_size:
            data = ''.join(self.buffer[self.pos:self.pos + current_size])
            builder.append(data)
        self._reader_reset_buf()
        # We're going past the buffer's bounds, flush it
        if self.writable:
            self._writer_flush_unlocked(space, restore_pos=True)

        while True:
            # Read until EOF or until read() would block
            w_data = space.call_method(self.w_raw, "read")
            if space.is_w(w_data, space.w_None):
                if current_size == 0:
                    return w_data
                break
            data = space.str_w(w_data)
            size = len(data)
            if size == 0:
                break
            builder.append(data)
            current_size += size
            if self.abs_pos != -1:
                self.abs_pos += size
        return space.wrap(builder.build())

    def _raw_read(self, space, buffer, start, length):
        length = intmask(length)
        w_buf = space.wrap(RawBuffer(buffer, start, length))
        w_size = space.call_method(self.w_raw, "readinto", w_buf)
        if space.is_w(w_size, space.w_None):
            raise BlockingIOError()
        size = space.int_w(w_size)
        if size < 0 or size > length:
            raise OperationError(space.w_IOError, space.wrap(
                "raw readinto() returned invalid length %d "
                "(should have been between 0 and %d)" % (size, length)))
        if self.abs_pos != -1:
            self.abs_pos += size
        return size

    def _fill_buffer(self, space):
        start = self.read_end
        if start == -1:
            start = 0
        length = self.buffer_size - start
        size = self._raw_read(space, self.buffer, start, length)
        if size > 0:
            self.read_end = self.raw_pos = start + size
        return size

    def _read_generic(self, space, n):
        """Generic read function: read from the stream until enough bytes are
           read, or until an EOF occurs or until read() would block."""
        current_size = self._readahead()
        if n <= current_size:
            return self._read_fast(n)

        result_buffer = ['\0'] * n
        remaining = n
        written = 0
        data = None
        if current_size:
            for i in range(current_size):
                result_buffer[written + i] = self.buffer[self.pos + i]
            remaining -= current_size
            written += current_size
        self._reader_reset_buf()

        # XXX potential bug in CPython? The following is not enabled.
        # We're going past the buffer's bounds, flush it
        ## if self.writable:
        ##     self._writer_flush_unlocked(space, restore_pos=True)

        # Read whole blocks, and don't buffer them
        while remaining > 0:
            r = self.buffer_size * (remaining // self.buffer_size)
            if r == 0:
                break
            try:
                size = self._raw_read(space, result_buffer, written, r)
            except BlockingIOError:
                if written == 0:
                    return None
                size = 0
            if size == 0:
                return ''.join(result_buffer[:written])
            remaining -= size
            written += size

        self.pos = 0
        self.raw_pos = 0
        self.read_end = 0

        while remaining > 0 and self.read_end < self.buffer_size:
            try:
                size = self._fill_buffer(space)
            except BlockingIOError:
                # EOF or read() would block
                if written == 0:
                    return None
                size = 0
            if size == 0:
                break

            if remaining > 0:
                if size > remaining:
                    size = remaining
                for i in range(size):
                    result_buffer[written + i] = self.buffer[self.pos + i]
                self.pos += size

                written += size
                remaining -= size

        return ''.join(result_buffer[:written])

    def _read_fast(self, n):
        """Read n bytes from the buffer if it can, otherwise return None.
           This function is simple enough that it can run unlocked."""
        current_size = self._readahead()
        if n <= current_size:
            endpos = self.pos + n
            res = ''.join(self.buffer[self.pos:endpos])
            self.pos = endpos
            return res
        return None

    # ____________________________________________________
    # Write methods

    def _adjust_position(self, new_pos):
        assert new_pos >= 0
        self.pos = new_pos
        if self.readable and self.read_end != -1 and self.read_end < new_pos:
            self.read_end = self.pos

    def write_w(self, space, w_data):
        self._check_init(space)
        self._check_closed(space, "write to closed file")
        data = space.bufferstr_w(w_data)
        size = len(data)

        with self.lock:

            if (not (self.readable and self.read_end != -1) and
                not (self.writable and self.write_end != -1)):
                self.pos = 0
                self.raw_pos = 0
            available = self.buffer_size - self.pos
            # Fast path: the data to write can be fully buffered
            if size <= available:
                for i in range(size):
                    self.buffer[self.pos + i] = data[i]
                if self.write_end == -1:
                    self.write_pos = self.pos
                self._adjust_position(self.pos + size)
                if self.pos > self.write_end:
                    self.write_end = self.pos
                return space.wrap(size)

            # First write the current buffer
            try:
                self._writer_flush_unlocked(space)
            except OperationError, e:
                if not e.match(space, space.gettypeobject(
                    W_BlockingIOError.typedef)):
                    raise
                w_exc = e.get_w_value(space)
                assert isinstance(w_exc, W_BlockingIOError)
                if self.readable:
                    self._reader_reset_buf()
                # Make some place by shifting the buffer
                for i in range(self.write_pos, self.write_end):
                    self.buffer[i - self.write_pos] = self.buffer[i]
                self.write_end -= self.write_pos
                self.raw_pos -= self.write_pos
                newpos = self.pos - self.write_pos
                assert newpos >= 0
                self.pos = newpos
                self.write_pos = 0
                available = self.buffer_size - self.write_end
                if size <= available:
                    # Everything can be buffered
                    for i in range(size):
                        self.buffer[self.write_end + i] = data[i]
                    self.write_end += size
                    return space.wrap(size)
                # Buffer as much as possible
                for i in range(available):
                    self.buffer[self.write_end + i] = data[i]
                    self.write_end += available
                # Raise previous exception
                w_exc.written = available
                raise

            # Adjust the raw stream position if it is away from the logical
            # stream position. This happens if the read buffer has been filled
            # but not modified (and therefore _bufferedwriter_flush_unlocked()
            # didn't rewind the raw stream by itself).
            offset = self._raw_offset()
            if offset:
                self._raw_seek(space, -offset, 1)
                self.raw_pos -= offset

            # Then write buf itself. At this point the buffer has been emptied
            remaining = size
            written = 0
            while remaining > self.buffer_size:
                try:
                    n = self._write(space, data[written:])
                except OperationError, e:
                    if not e.match(space, space.gettypeobject(
                        W_BlockingIOError.typedef)):
                        raise
                    w_exc = e.get_w_value(space)
                    assert isinstance(w_exc, W_BlockingIOError)
                    written += w_exc.written
                    remaining -= w_exc.written
                    if remaining > self.buffer_size:
                        # Can't buffer everything, still buffer as much as
                        # possible
                        for i in range(self.buffer_size):
                            self.buffer[i] = data[written + i]
                        self.raw_pos = 0
                        self._adjust_position(self.buffer_size)
                        self.write_end = self.buffer_size
                        w_exc.written = written + self.buffer_size
                        raise
                    break
                written += n
                remaining -= n
                # Partial writes can return successfully when interrupted by a
                # signal (see write(2)).  We must run signal handlers before
                # blocking another time, possibly indefinitely.
                space.getexecutioncontext().checksignals()

            if self.readable:
                self._reader_reset_buf()
            if remaining > 0:
                for i in range(remaining):
                    self.buffer[i] = data[written + i]
                written += remaining
            self.write_pos = 0
            self.write_end = remaining
            self._adjust_position(remaining)
            self.raw_pos = 0
        return space.wrap(written)

    def flush_w(self, space):
        self._check_init(space)
        self._check_closed(space, "flush of closed file")
        with self.lock:
            self._writer_flush_unlocked(space)
            if self.readable:
                # Rewind the raw stream so that its position corresponds to
                # the current logical position.
                self._raw_seek(space, -self._raw_offset(), 1)
                self._reader_reset_buf()


class W_BufferedReader(BufferedMixin, W_BufferedIOBase):
    @unwrap_spec(buffer_size=int)
    def descr_init(self, space, w_raw, buffer_size=DEFAULT_BUFFER_SIZE):
        self.state = STATE_ZERO
        check_readable_w(space, w_raw)

        self.w_raw = w_raw
        self.buffer_size = buffer_size
        self.readable = True

        self._init(space)
        self._reader_reset_buf()
        self.state = STATE_OK

W_BufferedReader.typedef = TypeDef(
    'BufferedReader', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedReader),
    __init__  = interp2app(W_BufferedReader.descr_init),
    __module__ = "_io",

    read = interp2app(W_BufferedReader.read_w),
    peek = interp2app(W_BufferedReader.peek_w),
    read1 = interp2app(W_BufferedReader.read1_w),
    raw = interp_attrproperty_w("w_raw", cls=W_BufferedReader),

    # from the mixin class
    __repr__ = interp2app(W_BufferedReader.repr_w),
    readable = interp2app(W_BufferedReader.readable_w),
    writable = interp2app(W_BufferedReader.writable_w),
    seekable = interp2app(W_BufferedReader.seekable_w),
    seek = interp2app(W_BufferedReader.seek_w),
    tell = interp2app(W_BufferedReader.tell_w),
    close = interp2app(W_BufferedReader.close_w),
    flush = interp2app(W_BufferedReader.simple_flush_w), # Not flush_w!
    detach = interp2app(W_BufferedReader.detach_w),
    truncate = interp2app(W_BufferedReader.truncate_w),
    fileno = interp2app(W_BufferedReader.fileno_w),
    isatty = interp2app(W_BufferedReader.isatty_w),
    closed = GetSetProperty(W_BufferedReader.closed_get_w),
    name = GetSetProperty(W_BufferedReader.name_get_w),
    mode = GetSetProperty(W_BufferedReader.mode_get_w),
)

class W_BufferedWriter(BufferedMixin, W_BufferedIOBase):
    @unwrap_spec(buffer_size=int, max_buffer_size=int)
    def descr_init(self, space, w_raw, buffer_size=DEFAULT_BUFFER_SIZE,
                   max_buffer_size=-234):
        if max_buffer_size != -234:
            self._deprecated_max_buffer_size(space)

        self.state = STATE_ZERO
        check_writable_w(space, w_raw)

        self.w_raw = w_raw
        self.buffer_size = buffer_size
        self.writable = True

        self._init(space)
        self._writer_reset_buf()
        self.state = STATE_OK

W_BufferedWriter.typedef = TypeDef(
    'BufferedWriter', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedWriter),
    __init__  = interp2app(W_BufferedWriter.descr_init),
    __module__ = "_io",

    write = interp2app(W_BufferedWriter.write_w),
    flush = interp2app(W_BufferedWriter.flush_w),
    raw = interp_attrproperty_w("w_raw", cls=W_BufferedWriter),

    # from the mixin class
    __repr__ = interp2app(W_BufferedWriter.repr_w),
    readable = interp2app(W_BufferedWriter.readable_w),
    writable = interp2app(W_BufferedWriter.writable_w),
    seekable = interp2app(W_BufferedWriter.seekable_w),
    seek = interp2app(W_BufferedWriter.seek_w),
    tell = interp2app(W_BufferedWriter.tell_w),
    close = interp2app(W_BufferedWriter.close_w),
    fileno = interp2app(W_BufferedWriter.fileno_w),
    isatty = interp2app(W_BufferedWriter.isatty_w),
    detach = interp2app(W_BufferedWriter.detach_w),
    truncate = interp2app(W_BufferedWriter.truncate_w),
    closed = GetSetProperty(W_BufferedWriter.closed_get_w),
    name = GetSetProperty(W_BufferedWriter.name_get_w),
    mode = GetSetProperty(W_BufferedWriter.mode_get_w),
)

def _forward_call(space, w_obj, method, __args__):
    w_meth = self.getattr(w_obj, self.wrap(method))
    return self.call_args(w_meth, __args__)

def make_forwarding_method(method, writer=False, reader=False):
    @func_renamer(method + '_w')
    def method_w(self, space, __args__):
        if writer:
            w_meth = space.getattr(self.w_writer, space.wrap(method))
            w_result = space.call_args(w_meth, __args__)
        if reader:
            w_meth = space.getattr(self.w_reader, space.wrap(method))
            w_result = space.call_args(w_meth, __args__)
        return w_result
    return method_w

class W_BufferedRWPair(W_BufferedIOBase):
    w_reader = None
    w_writer = None

    @unwrap_spec(buffer_size=int, max_buffer_size=int)
    def descr_init(self, space, w_reader, w_writer,
                   buffer_size=DEFAULT_BUFFER_SIZE, max_buffer_size=-234):
        if max_buffer_size != -234:
            self._deprecated_max_buffer_size(space)

        try:
            self.w_reader = W_BufferedReader(space)
            self.w_reader.descr_init(space, w_reader, buffer_size)
            self.w_writer = W_BufferedWriter(space)
            self.w_writer.descr_init(space, w_writer, buffer_size)
        except Exception:
            self.w_reader = None
            self.w_writer = None
            raise

    def destructor(self):
        # method overriden to not close the files
        pass

    # forward to reader
    for method in ['read', 'peek', 'read1', 'readinto', 'readable']:
        locals()[method + '_w'] = make_forwarding_method(
            method, reader=True)

    # forward to writer
    for method in ['write', 'flush', 'writable']:
        locals()[method + '_w'] = make_forwarding_method(
            method, writer=True)

    # forward to both
    for method in ['close']:
        locals()[method + '_w'] = make_forwarding_method(
            method, writer=True, reader=True)

    def isatty_w(self, space):
        if space.is_true(space.call_method(self.w_writer, "isatty")):
            return space.w_True
        return space.call_method(self.w_reader, "isatty")

    def closed_get_w(self, space):
        return space.getattr(self.w_writer, space.wrap("closed"))

methods = dict((method, interp2app(getattr(W_BufferedRWPair, method + '_w')))
               for method in ['read', 'peek', 'read1', 'readinto', 'readable',
                              'write', 'flush', 'writable',
                              'close',
                              'isatty'])

W_BufferedRWPair.typedef = TypeDef(
    '_io.BufferedRWPair', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRWPair),
    __init__  = interp2app(W_BufferedRWPair.descr_init),
    closed = GetSetProperty(W_BufferedRWPair.closed_get_w),
    **methods
)

class W_BufferedRandom(BufferedMixin, W_BufferedIOBase):
    @unwrap_spec(buffer_size=int, max_buffer_size=int)
    def descr_init(self, space, w_raw, buffer_size=DEFAULT_BUFFER_SIZE,
                   max_buffer_size = -234):
        if max_buffer_size != -234:
            self._deprecated_max_buffer_size(space)

        self.state = STATE_ZERO

        check_readable_w(space, w_raw)
        check_writable_w(space, w_raw)
        check_seekable_w(space, w_raw)

        self.w_raw = w_raw
        self.buffer_size = buffer_size
        self.readable = self.writable = True

        self._init(space)
        self._reader_reset_buf()
        self._writer_reset_buf()
        self.pos = 0
        self.state = STATE_OK

W_BufferedRandom.typedef = TypeDef(
    'BufferedRandom', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRandom),
    __init__ = interp2app(W_BufferedRandom.descr_init),
    __module__ = "_io",

    read = interp2app(W_BufferedRandom.read_w),
    peek = interp2app(W_BufferedRandom.peek_w),
    read1 = interp2app(W_BufferedRandom.read1_w),

    write = interp2app(W_BufferedRandom.write_w),
    flush = interp2app(W_BufferedRandom.flush_w),
    raw = interp_attrproperty_w("w_raw", cls=W_BufferedRandom),

    # from the mixin class
    __repr__ = interp2app(W_BufferedRandom.repr_w),
    readable = interp2app(W_BufferedRandom.readable_w),
    writable = interp2app(W_BufferedRandom.writable_w),
    seekable = interp2app(W_BufferedRandom.seekable_w),
    seek = interp2app(W_BufferedRandom.seek_w),
    tell = interp2app(W_BufferedRandom.tell_w),
    close = interp2app(W_BufferedRandom.close_w),
    detach = interp2app(W_BufferedRandom.detach_w),
    truncate = interp2app(W_BufferedRandom.truncate_w),
    fileno = interp2app(W_BufferedRandom.fileno_w),
    isatty = interp2app(W_BufferedRandom.isatty_w),
    closed = GetSetProperty(W_BufferedRandom.closed_get_w),
    name = GetSetProperty(W_BufferedRandom.name_get_w),
    mode = GetSetProperty(W_BufferedRandom.mode_get_w),
)
