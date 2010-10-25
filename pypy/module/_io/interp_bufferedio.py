from __future__ import with_statement
from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rstring import StringBuilder
from pypy.module._io.interp_iobase import W_IOBase, convert_size
from pypy.module._io.interp_io import DEFAULT_BUFFER_SIZE
from pypy.module.thread.os_lock import Lock

class W_BufferedIOBase(W_IOBase):
    def __init__(self, space):
        W_IOBase.__init__(self, space)
        self.buffer = lltype.nullptr(rffi.CCHARP.TO)
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

    def _unsupportedoperation(self, space, message):
        w_exc = space.getattr(space.getbuiltinmodule('_io'),
                              space.wrap('UnsupportedOperation'))
        raise OperationError(w_exc, space.wrap(message))

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._unsupportedoperation(space, "read")

W_BufferedIOBase.typedef = TypeDef(
    '_BufferedIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_BufferedIOBase),
    read = interp2app(W_BufferedIOBase.read_w),
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
        self._reset_buf()

    def _reset_buf(self):
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
        builder = StringBuilder()
        # First copy what we have in the current buffer
        current_size = self._readahead()
        data = None
        if current_size:
            data = rffi.charpsize2str(rffi.ptradd(self.buffer, self.pos),
                                      current_size)
            builder.append(data)
        self._reset_buf()
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
        self._reset_buf()

        # XXX potential bug in CPython? The following is not enabled.
        # We're going past the buffer's bounds, flush it
        ## if self.writable:
        ##     self._writer_flush_unlocked(restore_pos=True)

        while remaining > 0:
            # Read until EOF or until read() would block
            w_data = space.call_method(self.raw, "read", space.wrap(remaining))
            if space.is_w(w_data, space.w_None):
                break
            data = space.str_w(w_data)
            size = len(data)
            if size == 0:
                break
            builder.append(data)
            current_size += size
            remaining -= size
            if self.abs_pos != -1:
                self.abs_pos += size
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

