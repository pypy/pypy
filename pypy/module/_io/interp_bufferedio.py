from __future__ import with_statement
from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.rarithmetic import r_longlong
from pypy.module._io.interp_iobase import W_IOBase, convert_size
from pypy.module._io.interp_io import DEFAULT_BUFFER_SIZE, W_BlockingIOError
from pypy.module.thread.os_lock import Lock

class BlockingIOError(Exception):
    pass

class W_BufferedIOBase(W_IOBase):
    def __init__(self, space):
        W_IOBase.__init__(self, space)

        self.buffer = lltype.nullptr(rffi.CCHARP.TO)
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

    def _unsupportedoperation(self, space, message):
        w_exc = space.getattr(space.getbuiltinmodule('_io'),
                              space.wrap('UnsupportedOperation'))
        raise OperationError(w_exc, space.wrap(message))

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._unsupportedoperation(space, "read")

    @unwrap_spec('self', ObjSpace, W_Root)
    def write_w(self, space, w_size=None):
        self._unsupportedoperation(space, "write")

    def _reader_reset_buf(self):
        self.read_end = -1

    def _writer_reset_buf(self):
        self.write_pos = 0
        self.write_end = -1

W_BufferedIOBase.typedef = TypeDef(
    '_BufferedIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_BufferedIOBase),
    read = interp2app(W_BufferedIOBase.read_w),
    write = interp2app(W_BufferedIOBase.write_w),
    )

class BufferedMixin:
    _mixin_ = True

    def _init(self, space):
        if self.buffer_size <= 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "buffer size must be strictly positive"))

        if self.buffer:
            lltype.free(self.buffer, flavor='raw')
        self.buffer = lltype.malloc(rffi.CCHARP.TO, self.buffer_size,
                                    flavor='raw')

        ## XXX cannot free a Lock?
        ## if self.lock:
        ##     self.lock.free()
        self.lock = Lock(space)

        try:
            self._raw_tell(space)
        except OperationError:
            pass

    def _raw_tell(self, space):
        w_pos = space.call_method(self.raw, "tell")
        pos = space.r_longlong_w(w_pos)
        if pos < 0:
            raise OperationError(space.w_IOError, space.wrap(
                "raw stream returned invalid position"))

        self.abs_pos = pos
        return pos

    def _readahead(self):
        if self.readable and self.read_end != -1:
            return self.read_end - self.pos
        return 0

    def _raw_offset(self):
        if self.raw_pos >= 0 and (
            (self.readable and self.read_end != -1) or
            (self.writable and self.write_end != -1)):
            return self.raw_pos - self.pos
        return 0

    @unwrap_spec('self', ObjSpace, r_longlong, int)
    def seek_w(self, space, pos, whence=0):
        if whence not in (0, 1, 2):
            raise operationerrfmt(space.w_ValueError,
                "whence must be between 0 and 2, not %d", whence)
        self._check_closed(space, "seek of closed file")
        if whence != 2 and self.readable:
            # Check if seeking leaves us inside the current buffer, so as to
            # return quickly if possible. Also, we needn't take the lock in
            # this fast path.
            current = self._raw_tell(space)
            available = self._readahead()
            if available > 0:
                if whence == 0:
                    offset = pos - (current - self._raw_offset())
                else:
                    offset = pos
                if -self.pos <= offset <= available:
                    self.pos += offset
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
        w_pos = space.call_method(self.raw, "seek",
                                  space.wrap(pos), space.wrap(whence))
        pos = space.r_longlong_w(w_pos)
        if pos < 0:
            raise OperationError(space.w_IOError, space.wrap(
                "Raw stream returned invalid position"))
        return pos

    def _closed(self, space):
        return self.raw._closed(space)

    @unwrap_spec('self', ObjSpace)
    def close_w(self, space):
        with self.lock:
            if self._closed(space):
                return
        space.call_method(self, "flush")
        with self.lock:
            space.call_method(self.raw, "close")

    @unwrap_spec('self', ObjSpace)
    def flush_w(self, space):
        return space.call_method(self.raw, "flush")

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
                self.write_pos += e.written
                self.raw_pos = self.write_pos
                written += e.written
                # re-raise the error
                e.written = written
                raise
            self.write_pos += n
            self.raw_pos = self.write_pos
            written += n
            # Partial writes can return successfully when interrupted by a
            # signal (see write(2)).  We must run signal handlers before
            # blocking another time, possibly indefinitely.
            # XXX PyErr_CheckSignals()

        if restore_pos:
            forward = rewind - written
            if forward:
                self._raw_seek(space, forward, 1)
                self.raw_pos += forward

        self._writer_reset_buf()

    def _write(self, space, data):
        w_data = space.wrap(data)
        w_written = space.call_method(self.raw, "write", w_data)
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

class W_BufferedReader(W_BufferedIOBase, BufferedMixin):
    def __init__(self, space):
        W_BufferedIOBase.__init__(self, space)
        self.ok = False
        self.detached = False

    @unwrap_spec('self', ObjSpace, W_Root, int)
    def descr_init(self, space, w_raw, buffer_size=DEFAULT_BUFFER_SIZE):
        raw = space.interp_w(W_IOBase, w_raw)
        raw.check_readable_w(space)

        self.raw = raw
        self.buffer_size = buffer_size
        self.readable = True

        self._init(space)
        self._reader_reset_buf()

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._check_closed(space, "read of closed file")
        size = convert_size(space, w_size)

        if size < 0:
            # read until the end of stream
            with self.lock:
                res = self._read_all(space)
        else:
            res = self._read_fast(size)
            if res is None:
                with self.lock:
                    res = self._read_generic(space, size)
        return space.wrap(res)

    def _read_all(self, space):
        "Read all the file, don't update the cache"
        builder = StringBuilder()
        # First copy what we have in the current buffer
        current_size = self._readahead()
        data = None
        if current_size:
            data = rffi.charpsize2str(rffi.ptradd(self.buffer, self.pos),
                                      current_size)
            builder.append(data)
        self._reader_reset_buf()
        # We're going past the buffer's bounds, flush it
        if self.writable:
            self._writer_flush_unlocked(space, restore_pos=True)

        while True:
            # Read until EOF or until read() would block
            w_data = space.call_method(self.raw, "read")
            if space.is_w(w_data, space.w_None):
                break
            data = space.str_w(w_data)
            size = len(data)
            if size == 0:
                break
            builder.append(data)
            current_size += size
            if self.abs_pos != -1:
                self.abs_pos += size
        return builder.build()

    def _raw_read(self, space, n):
        w_data = space.call_method(self.raw, "read", space.wrap(n))
        if space.is_w(w_data, space.w_None):
            raise BlockingIOError()
        data = space.str_w(w_data)
        if self.abs_pos != -1:
            self.abs_pos += len(data)
        return data

    def _fill_buffer(self, space):
        start = self.read_end
        if start == -1:
            start = 0
        length = self.buffer_size - start
        data = self._raw_read(space, length)
        size = len(data)
        if size > 0:
            for i in range(start, start + size):
                self.buffer[i] = data[i]
            self.read_end = self.raw_pos = start + size
        return size

    def _read_generic(self, space, n):
        """Generic read function: read from the stream until enough bytes are
           read, or until an EOF occurs or until read() would block."""
        current_size = self._readahead()
        if n <= current_size:
            return self._read_fast(n)

        builder = StringBuilder(n)
        remaining = n
        written = 0
        data = None
        if current_size:
            data = rffi.charpsize2str(rffi.ptradd(self.buffer, self.pos),
                                      current_size)
            builder.append(data)
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
                data = self._raw_read(space, r)
            except BlockingIOError:
                if written == 0:
                    return None
                data = ""
            size = len(data)
            if size == 0:
                return builder.build()
            remaining -= size
            written += size

        self.pos = 0
        self.raw_pos = 0
        self.read_end = 0

        while remaining > 0 and self.read_end < self.buffer_size:
            # Read until EOF or until read() would block
            try:
                size = self._fill_buffer(space)
            except BlockingIOError:
                if written == 0:
                    return None
                break

            if remaining > 0:
                if size > remaining:
                    size = remaining
                # XXX inefficient
                l = []
                for i in range(self.pos,self.pos + size):
                    l.append(self.buffer[i])
                data = ''.join(l)
                builder.append(data)

                written += size
                self.pos += size
                remaining -= size
        return builder.build()

    def _read_fast(self, n):
        """Read n bytes from the buffer if it can, otherwise return None.
           This function is simple enough that it can run unlocked."""
        current_size = self._readahead()
        if n <= current_size:
            res = rffi.charpsize2str(rffi.ptradd(self.buffer, self.pos), n)
            self.pos += n
            return res
        return None

W_BufferedReader.typedef = TypeDef(
    'BufferedReader', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedReader),
    __init__  = interp2app(W_BufferedReader.descr_init),

    read = interp2app(W_BufferedReader.read_w),

    # from the mixin class
    seek = interp2app(W_BufferedReader.seek_w),
    close = interp2app(W_BufferedReader.close_w),
    flush = interp2app(W_BufferedReader.flush_w),
    )

class W_BufferedWriter(W_BufferedIOBase, BufferedMixin):
    @unwrap_spec('self', ObjSpace, W_Root, int)
    def descr_init(self, space, w_raw, buffer_size=DEFAULT_BUFFER_SIZE):
        raw = space.interp_w(W_IOBase, w_raw)
        raw.check_writable_w(space)

        self.raw = raw
        self.buffer_size = buffer_size
        self.writable = True

        self._init(space)
        self._writer_reset_buf()

    def _adjust_position(self, new_pos):
        self.pos = new_pos
        if self.readable and self.read_end != -1 and self.read_end < new_pos:
            self.read_end = self.pos

    @unwrap_spec('self', ObjSpace, W_Root)
    def write_w(self, space, w_data):
        self._check_closed(space, "write to closed file")
        data = space.str_w(w_data)
        size = len(data)

        with self.lock:

            if (not (self.readable and self.read_end == -1) and
                not (self.writable and self.write_end == -1)):
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
                if self.readable:
                    self._reader_reset_buf()
                # Make some place by shifting the buffer
                for i in range(self.write_pos, self.write_end):
                    self.buffer[i - self.write_pos] = self.buffer[i]
                self.write_end -= self.write_pos
                self.raw_pos -= self.write_pos
                self.pos -= self.write_pos
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
                e.written = available
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
                    written += e.written
                    remaining -= e.written
                    if remaining > self.buffer_size:
                        # Can't buffer everything, still buffer as much as
                        # possible
                        for i in range(self.buffer_size):
                            self.buffer[i] = data[written + i]
                        self.raw_pos = 0
                        self._adjust_position(self.buffer_size)
                        self.write_end = self.buffer_size
                        e.written = written + self.buffer_size
                        raise
                    break
                written += n
                remaining -= n
                # Partial writes can return successfully when interrupted by a
                # signal (see write(2)).  We must run signal handlers before
                # blocking another time, possibly indefinitely.
                # XXX PyErr_CheckSignals()

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

    @unwrap_spec('self', ObjSpace)
    def flush_w(self, space):
        self._check_closed(space, "flush of closed file")
        with self.lock:
            self._writer_flush_unlocked(space)
            if self.readable:
                # Rewind the raw stream so that its position corresponds to
                # the current logical position.
                self._raw_seek(space, -self._raw_offset(), 1)
                self._reader_reset_buf()

W_BufferedWriter.typedef = TypeDef(
    'BufferedWriter', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedWriter),
    __init__  = interp2app(W_BufferedWriter.descr_init),

    write = interp2app(W_BufferedWriter.write_w),
    flush = interp2app(W_BufferedWriter.flush_w),

    # from the mixin class
    seek = interp2app(W_BufferedWriter.seek_w),
    close = interp2app(W_BufferedWriter.close_w),
    )

class W_BufferedRWPair(W_BufferedIOBase):
    pass
W_BufferedRWPair.typedef = TypeDef(
    'BufferedRWPair', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRWPair),
    )

class W_BufferedRandom(W_BufferedIOBase):
    pass
W_BufferedRandom.typedef = TypeDef(
    'BufferedRandom', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRandom),
    )

