from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
import sys

INVALID_HANDLE_VALUE = -1
READABLE = 1
WRITABLE = 2

PY_SSIZE_T_MAX = sys.maxint
PY_SSIZE_T_MIN = -sys.maxint - 1

class W_BaseConnection(Wrappable):
    def __init__(self, handle, flags):
        self.handle = handle
        self.flags = flags

    def descr_repr(self, space):
        conn_type = ["read-only", "write-only", "read-write"][self.flags]

        return space.wrap("<%s %s, handle %zd>" % (
            conn_type, space.type(self).getname(space, '?'), self.handle))

    def close(self):
        if self.handle != INVALID_HANDLE_VALUE:
            self.do_close()
            self.handle = INVALID_HANDLE_VALUE

    def __del__(self):
        self.close()

    def closed_get(space, self):
        return space.w_bool(self.handle == INVALID_HANDLE_VALUE)
    def readable_get(space, self):
        return space.w_bool(self.flags & READABLE)
    def writable_get(space, self):
        return space.w_bool(self.flags & WRITABLE)

    @unwrap_spec('self', ObjSpace, 'bufferstr', 'index', 'index')
    def send_bytes(self, space, buffer, offset=0, size=PY_SSIZE_T_MIN):
        length = len(buffer)
        self._check_writable()
        if offset < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("offset is negative"))
        if length < offset:
            raise OperationError(space.w_ValueError,
                                 space.wrap("buffer length < offset"))

        if size == PY_SSIZE_T_MIN:
            size = length - offset
        elif size < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("size is negative"))
        elif offset + size > length:
            raise OperationError(space.w_ValueError,
                                 space.wrap("buffer length > offset + size"))

        res = self.do_send_string(buffer, offset, size)
        if res < 0:
            raise mp_error(res)

    @unwrap_spec('self', ObjSpace, 'index')
    def recv_bytes(self, space, maxlength=sys.maxint):
        self._check_readable()
        if maxlength < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("maxlength < 0"))

        try:
            res, newbuf = self.do_recv_string(maxlength)

            if res < 0:
                if res == MP_BAD_MESSAGE_LENGTH:
                    self.flags &= ~READABLE
                    if self.flags == 0:
                        self.close()
                raise mp_error(res)

            if newbuf is not None:
                return space.wrap(rffi.charp2str(newbuf, res))
            else:
                return space.wrap(rffi.charp2str(self.buffer, res))
            return result
        finally:
            if newbuf is not None:
                rffi.free_charp(newbuf)

    @unwrap_spec('self', ObjSpace, W_Root, 'index')
    def recv_bytes_into(self, space, w_buffer, offset=0):
        rwbuffer = space.rwbuffer_w(w_buffer)
        length = rwbuffer.getlength()

        try:
            res, newbuf = self.do_recv_string(length - offset)

            if res < 0:
                if res == MP_BAD_MESSAGE_LENGTH:
                    self.flags &= ~READABLE
                    if self.flags == 0:
                        self.close()
                raise mp_error(res)

            if res > length - offset:
                raise OperationError(BufferTooShort)
            if newbuf is not None:
                rwbuffer.setslice(offset, newbuf)
            else:
                rwbuffer.setslice(offset, self.buffer)
        finally:
            if newbuf is not None:
                rffi.free_charp(newbuf)

        return space.wrap(res)


base_typedef = TypeDef(
    'BaseConnection',
    closed = GetSetProperty(W_BaseConnection.closed_get),
    readable = GetSetProperty(W_BaseConnection.readable_get),
    writable = GetSetProperty(W_BaseConnection.writable_get),

    send_bytes = interp2app(W_BaseConnection.send_bytes),
    recv_bytes = interp2app(W_BaseConnection.recv_bytes),
    recv_bytes_into = interp2app(W_BaseConnection.recv_bytes_into),
    ## send = interp2app(W_BaseConnection.send),
    ## recv = interp2app(W_BaseConnection.recv),
    ## poll = interp2app(W_BaseConnection.poll),
    ## fileno = interp2app(W_BaseConnection.fileno),
    ## close = interp2app(W_BaseConnection.close),
    )

class W_SocketConnection(W_BaseConnection):
    pass

W_SocketConnection.typedef = TypeDef(
    'Connection', base_typedef
)

class W_PipeConnection(W_BaseConnection):
    pass

W_PipeConnection.typedef = TypeDef(
    'PipeConnection', base_typedef
)
