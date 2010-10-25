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
from pypy.module._io.interp_io import DEFAULT_BUFFER_SIZE
from pypy.module.thread.os_lock import Lock

class BlockingIOError(Exception):
    pass

class W_BufferedIOBase(W_IOBase):
    def __init__(self, space):
        W_IOBase.__init__(self, space)
        self.buffer = lltype.nullptr(rffi.CCHARP.TO)
        self.pos = 0     # Current logical position in the buffer
        self.raw_pos = 0 # Position of the raw stream in the buffer.
        self.lock = None

        self.readable = False
        self.writable = False

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
        if self.raw_pos and (
            (self.readable and self.read_end != -1) or
            (self.writable and self.write_end != -1)):
            return self.raw_pos - self.pos
        return 0

    def _unsupportedoperation(self, space, message):
        w_exc = space.getattr(space.getbuiltinmodule('_io'),
                              space.wrap('UnsupportedOperation'))
        raise OperationError(w_exc, space.wrap(message))

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._unsupportedoperation(space, "read")

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
                self._writer_flush_unlocked(restore_pos=False)
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

W_BufferedIOBase.typedef = TypeDef(
    '_BufferedIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_BufferedIOBase),
    read = interp2app(W_BufferedIOBase.read_w),
    seek = interp2app(W_BufferedIOBase.seek_w),
    )

class W_BufferedReader(W_BufferedIOBase):
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

    def _reader_reset_buf(self):
        self.read_end = -1

    def _closed(self, space):
        return self.raw._closed(space)

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
            self._writer_flush_unlocked(restore_pos=True)

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
        ##     self._writer_flush_unlocked(restore_pos=True)

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
    )

class W_BufferedWriter(W_BufferedIOBase):
    pass
W_BufferedWriter.typedef = TypeDef(
    'BufferedWriter', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedWriter),
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

