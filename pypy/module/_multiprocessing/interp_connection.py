from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.rpython.lltypesystem import rffi, lltype
import sys

READABLE = 1
WRITABLE = 2

PY_SSIZE_T_MAX = sys.maxint
PY_SSIZE_T_MIN = -sys.maxint - 1

class W_BaseConnection(Wrappable):
    BUFFER_SIZE = 1024

    def __init__(self, handle, flags):
        self.handle = handle
        self.flags = flags

        self.buffer = lltype.malloc(rffi.CCHARP.TO, self.BUFFER_SIZE,
                                    flavor='raw')

    def __del__(self):
        lltype.free(self.buffer, flavor='raw')
        self.do_close()

    def descr_repr(self, space):
        conn_type = ["read-only", "write-only", "read-write"][self.flags]

        return space.wrap("<%s %s, handle %zd>" % (
            conn_type, space.type(self).getname(space, '?'), self.handle))

    def close(self):
        self.do_close()

    def closed_get(space, self):
        return space.w_bool(not self.is_valid())
    def readable_get(space, self):
        return space.w_bool(self.flags & READABLE)
    def writable_get(space, self):
        return space.w_bool(self.flags & WRITABLE)

    def _check_readable(self, space):
        if not self.flags & READABLE:
            raise OperationError(space.w_IOError,
                                 space.wrap("connection is write-only"))
    def _check_writable(self, space):
        if not self.flags & WRITABLE:
            raise OperationError(space.w_IOError,
                                 space.wrap("connection is read-only"))

    @unwrap_spec('self', ObjSpace, 'bufferstr', 'index', 'index')
    def send_bytes(self, space, buffer, offset=0, size=PY_SSIZE_T_MIN):
        length = len(buffer)
        self._check_writable(space)
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

        self.do_send_string(space, buffer, offset, size)

    @unwrap_spec('self', ObjSpace, 'index')
    def recv_bytes(self, space, maxlength=PY_SSIZE_T_MAX):
        self._check_readable(space)
        if maxlength < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("maxlength < 0"))

        res, newbuf = self.do_recv_string(space, maxlength)
        try:
            if res < 0:
                if res == MP_BAD_MESSAGE_LENGTH:
                    self.flags &= ~READABLE
                    if self.flags == 0:
                        self.close()
                raise mp_error(res)

            if newbuf:
                return space.wrap(rffi.charpsize2str(newbuf, res))
            else:
                return space.wrap(rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

    @unwrap_spec('self', ObjSpace, W_Root, 'index')
    def recv_bytes_into(self, space, w_buffer, offset=0):
        rwbuffer = space.rwbuffer_w(w_buffer)
        length = rwbuffer.getlength()

        res, newbuf = self.do_recv_string(space, length - offset)
        try:
            if res < 0:
                if res == MP_BAD_MESSAGE_LENGTH:
                    self.flags &= ~READABLE
                    if self.flags == 0:
                        self.close()
                raise mp_error(res)

            if res > length - offset:
                raise OperationError(BufferTooShort)
            if newbuf:
                rwbuffer.setslice(offset, rffi.charpsize2str(newbuf, res))
            else:
                rwbuffer.setslice(offset, rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

        return space.wrap(res)

    @unwrap_spec('self', ObjSpace, W_Root)
    def send(self, space, w_obj):
        self._check_writable(space)

        w_builtins = space.getbuiltinmodule('__builtin__')
        w_picklemodule = space.call_method(
            w_builtins, '__import__', space.wrap("pickle"))
        w_protocol = space.getattr(
            w_picklemodule, space.wrap("HIGHEST_PROTOCOL"))
        w_pickled = space.call_method(
            w_picklemodule, "dumps", w_obj, w_protocol)

        buffer = space.bufferstr_w(w_pickled)
        self.do_send_string(space, buffer, 0, len(buffer))

    @unwrap_spec('self', ObjSpace)
    def recv(self, space):
        self._check_readable(space)

        res, newbuf = self.do_recv_string(space, PY_SSIZE_T_MAX)
        try:
            if res < 0:
                if res == MP_BAD_MESSAGE_LENGTH:
                    self.flags &= ~READABLE
                    if self.flags == 0:
                        self.close()
                raise mp_error(res)
            if newbuf:
                w_received = space.wrap(rffi.charpsize2str(newbuf, res))
            else:
                w_received = space.wrap(rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

        w_builtins = space.getbuiltinmodule('__builtin__')
        w_picklemodule = space.call_method(
            w_builtins, '__import__', space.wrap("pickle"))
        w_unpickled = space.call_method(
            w_picklemodule, "loads", w_received)

        return w_unpickled



base_typedef = TypeDef(
    'BaseConnection',
    closed = GetSetProperty(W_BaseConnection.closed_get),
    readable = GetSetProperty(W_BaseConnection.readable_get),
    writable = GetSetProperty(W_BaseConnection.writable_get),

    send_bytes = interp2app(W_BaseConnection.send_bytes),
    recv_bytes = interp2app(W_BaseConnection.recv_bytes),
    recv_bytes_into = interp2app(W_BaseConnection.recv_bytes_into),
    send = interp2app(W_BaseConnection.send),
    recv = interp2app(W_BaseConnection.recv),
    ## poll = interp2app(W_BaseConnection.poll),
    ## fileno = interp2app(W_BaseConnection.fileno),
    close = interp2app(W_BaseConnection.close),
    )

class W_SocketConnection(W_BaseConnection):
    pass

W_SocketConnection.typedef = TypeDef(
    'Connection', base_typedef,
)

class W_PipeConnection(W_BaseConnection):
    if sys.platform == 'win32':
        from pypy.rlib.rwin32 import INVALID_HANDLE_VALUE

    @unwrap_spec(ObjSpace, W_Root, W_Root, bool, bool)
    def descr_new(space, w_subtype, w_handle, readable=True, writable=True):
        from pypy.module._multiprocessing.interp_win32 import handle_w
        handle = handle_w(space, w_handle)
        flags = (readable and READABLE) | (writable and WRITABLE)

        self = space.allocate_instance(W_PipeConnection, w_subtype)
        W_PipeConnection.__init__(self, handle, flags)
        return space.wrap(self)

    def is_valid(self):
        return self.handle != self.INVALID_HANDLE_VALUE

    def do_close(self):
        from pypy.rlib.rwin32 import CloseHandle
        if self.is_valid():
            CloseHandle(self.handle)
            self.handle = self.INVALID_HANDLE_VALUE

    def do_send_string(self, space, buffer, offset, size):
        from pypy.module._multiprocessing.interp_win32 import (
            _WriteFile, ERROR_NO_SYSTEM_RESOURCES)
        from pypy.rlib import rwin32

        charp = rffi.str2charp(buffer)
        written_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                    flavor='raw')
        try:
            result = _WriteFile(
                self.handle, rffi.ptradd(charp, offset),
                size, written_ptr, rffi.NULL)

            if (result == 0 and
                rwin32.GetLastError() == ERROR_NO_SYSTEM_RESOURCES):
                raise operrfmt(
                    space.w_ValueError,
                    "Cannot send %ld bytes over connection", size)
        finally:
            rffi.free_charp(charp)
            lltype.free(written_ptr, flavor='raw')

    def do_recv_string(self, space, maxlength):
        from pypy.module._multiprocessing.interp_win32 import (
            _ReadFile)
        from pypy.rlib import rwin32

        read_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                 flavor='raw')
        left_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                 flavor='raw')
        try:
            result = _ReadFile(self.handle,
                               self.buffer, min(self.BUFFER_SIZE, maxlength),
                               read_ptr, rffi.NULL)
            if result:
                return read_ptr[0], None

            err = rwin32.GetLastError()
            if err == ERROR_BROKEN_PIPE:
                return MP_END_OF_FILE
            elif err != ERROR_MORE_DATA:
                return MP_STANDARD_ERROR

            # More data...
            if not _PeekNamedPipe(self.handle, rffi.NULL, 0,
                                  rffi.NULL, rffi.NULL, left_ptr):
                return MP_STANDARD_ERROR

            length = read_ptr[0] + left_ptr[0]
            if length > maxlength:
                return MP_BAD_MESSAGE_LENGTH

            newbuf = lltype.malloc(rffi.CCHARP.TO, length + 1, flavor='raw')
            raw_memcopy(self.buffer, newbuf, read_ptr[0])

            result = _ReadFile(self.handle,
                               rffi.ptradd(newbuf, read_ptr[0]), left_ptr[0],
                               read_ptr, rffi.NULL)
            if result:
                assert read_ptr[0] == left_ptr[0]
                return length, newbuf
            else:
                rffi.free_charp(newbuf)
                return MP_STANDARD_ERROR, None
        finally:
            lltype.free(read_ptr, flavor='raw')

W_PipeConnection.typedef = TypeDef(
    'PipeConnection', base_typedef,
    __new__ = interp2app(W_PipeConnection.descr_new.im_func),
)
