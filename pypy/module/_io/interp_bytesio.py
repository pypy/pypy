from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr, GetSetProperty)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rlib.rarithmetic import r_longlong
from pypy.module._io.interp_bufferedio import W_BufferedIOBase
from pypy.module._io.interp_iobase import convert_size
import sys

def buffer2string(buffer, start, end):
    from pypy.rlib.rstring import StringBuilder
    builder = StringBuilder(end - start)
    for i in range(start, end):
        builder.append(buffer[i])
    return builder.build()

class W_BytesIO(W_BufferedIOBase):
    def __init__(self, space):
        W_BufferedIOBase.__init__(self, space)
        self.pos = 0
        self.string_size = 0
        self.buf = None

    def descr_init(self, space, w_initial_bytes=None):
        # In case __init__ is called multiple times
        self.buf = []
        self.string_size = 0
        self.pos = 0

        if not space.is_w(w_initial_bytes, space.w_None):
            self.write_w(space, w_initial_bytes)
            self.pos = 0

    def _check_closed(self, space, message=None):
        if self.buf is None:
            if message is None:
                message = "I/O operation on closed file"
            raise OperationError(space.w_ValueError, space.wrap(message))

    def read_w(self, space, w_size=None):
        self._check_closed(space)
        size = convert_size(space, w_size)

        # adjust invalid sizes
        available = self.string_size - self.pos
        if not 0 <= size <= available:
            size = available
            if size < 0:
                size = 0

        output = buffer2string(self.buf, self.pos, self.pos + size)
        self.pos += size
        return space.wrap(output)

    def read1_w(self, space, w_size):
        return self.read_w(space, w_size)

    def readinto_w(self, space, w_buffer):
        self._check_closed(space)
        rwbuffer = space.rwbuffer_w(w_buffer)
        size = rwbuffer.getlength()

        if self.pos + size > self.string_size:
            size = self.string_size - self.pos

        output = buffer2string(self.buf, self.pos, self.pos + size)
        length = len(output)
        rwbuffer.setslice(0, output)
        self.pos += length
        return space.wrap(length)

    def write_w(self, space, w_data):
        self._check_closed(space)
        if space.isinstance_w(w_data, space.w_unicode):
            raise OperationError(space.w_TypeError, space.wrap(
                "bytes string of buffer expected"))
        buf = space.buffer_w(w_data)
        length = buf.getlength()
        if length <= 0:
            return

        if self.pos + length > len(self.buf):
            self.buf.extend(['\0'] * (self.pos + length - len(self.buf)))

        if self.pos > self.string_size:
            # In case of overseek, pad with null bytes the buffer region
            # between the end of stream and the current position.
            #
            # 0   lo      string_size                           hi
            # |   |<---used--->|<----------available----------->|
            # |   |            <--to pad-->|<---to write--->    |
            # 0   buf                   position
            for i in range(self.string_size, self.pos):
                self.buf[i] = '\0'

        # Copy the data to the internal buffer, overwriting some of the
        # existing data if self->pos < self->string_size.
        for i in range(length):
            self.buf[self.pos + i] = buf.getitem(i)
        self.pos += length

        # Set the new length of the internal string if it has changed
        if self.string_size < self.pos:
            self.string_size = self.pos

        return space.wrap(length)

    def truncate_w(self, space, w_size=None):
        self._check_closed(space)

        if space.is_w(w_size, space.w_None):
            size = self.pos
        else:
            size = space.r_longlong_w(w_size)

        if size < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "negative size value"))

        if size < self.string_size:
            self.string_size = size
            del self.buf[size:]

        return space.wrap(size)

    def getvalue_w(self, space):
        self._check_closed(space)
        return space.wrap(buffer2string(self.buf, 0, self.string_size))

    def tell_w(self, space):
        self._check_closed(space)
        return space.wrap(self.pos)

    @unwrap_spec(pos=r_longlong, whence=int)
    def seek_w(self, space, pos, whence=0):
        self._check_closed(space)

        if whence == 0:
            if pos < 0:
                raise OperationError(space.w_ValueError, space.wrap(
                    "negative seek value"))
        elif whence == 1:
            if pos > sys.maxint - self.pos:
                raise OperationError(space.w_OverflowError, space.wrap(
                    "new position too large"))
            pos += self.pos
        elif whence == 2:
            if pos > sys.maxint - self.string_size:
                raise OperationError(space.w_OverflowError, space.wrap(
                    "new position too large"))
            pos += self.string_size
        else:
            raise operationerrfmt(space.w_ValueError,
                "whence must be between 0 and 2, not %d", whence)

        if pos >= 0:
            self.pos = pos
        else:
            self.pos = 0
        return space.wrap(self.pos)

    def readable_w(self, space):
        return space.w_True

    def writable_w(self, space):
        return space.w_True

    def seekable_w(self, space):
        return space.w_True

    def close_w(self, space):
        self.buf = None

    def closed_get_w(self, space):
        return space.wrap(self.buf is None)

    def getstate_w(self, space):
        self._check_closed(space)
        w_content = space.wrap(buffer2string(self.buf, 0, self.string_size))
        return space.newtuple([
            w_content,
            space.wrap(self.pos),
            self.getdict(space)])

    def setstate_w(self, space, w_state):
        self._check_closed(space)

        if space.len_w(w_state) != 3:
            raise operationerrfmt(space.w_TypeError,
                "%s.__setstate__ argument should be 3-tuple, got %s",
                space.type(self).getname(space),
                space.type(w_state).getname(space)
            )
        w_content, w_pos, w_dict = space.unpackiterable(w_state, 3)
        pos = space.int_w(w_pos)
        self.buf = []
        self.write_w(space, w_content)
        if pos < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "position value cannot be negative"))
        self.pos = pos
        if not space.is_w(w_dict, space.w_None):
            space.call_method(self.getdict(space), "update", w_dict)

W_BytesIO.typedef = TypeDef(
    'BytesIO', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BytesIO),
    __init__  = interp2app(W_BytesIO.descr_init),

    read = interp2app(W_BytesIO.read_w),
    read1 = interp2app(W_BytesIO.read1_w),
    readinto = interp2app(W_BytesIO.readinto_w),
    write = interp2app(W_BytesIO.write_w),
    truncate = interp2app(W_BytesIO.truncate_w),
    getvalue = interp2app(W_BytesIO.getvalue_w),
    seek = interp2app(W_BytesIO.seek_w),
    tell = interp2app(W_BytesIO.tell_w),
    readable = interp2app(W_BytesIO.readable_w),
    writable = interp2app(W_BytesIO.writable_w),
    seekable = interp2app(W_BytesIO.seekable_w),
    close = interp2app(W_BytesIO.close_w),
    closed = GetSetProperty(W_BytesIO.closed_get_w),
    __getstate__ = interp2app(W_BytesIO.getstate_w),
    __setstate__ = interp2app(W_BytesIO.setstate_w),
    )
