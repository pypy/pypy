from __future__ import with_statement
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import (
    OperationError, wrap_oserror, operationerrfmt)
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import rpoll
import sys

READABLE = 1
WRITABLE = 2

PY_SSIZE_T_MAX = sys.maxint
PY_SSIZE_T_MIN = -sys.maxint - 1

def BufferTooShort(space, w_data):
    w_builtins = space.getbuiltinmodule('__builtin__')
    w_module = space.call_method(
        w_builtins, '__import__', space.wrap("multiprocessing"))
    w_BufferTooShort = space.getattr(w_module, space.wrap("BufferTooShort"))
    return OperationError(w_BufferTooShort, w_data)

def w_handle(space, handle):
    return space.wrap(rffi.cast(rffi.INTPTR_T, handle))

class W_BaseConnection(Wrappable):
    BUFFER_SIZE = 1024

    def __init__(self, flags):
        self.flags = flags
        self.buffer = lltype.malloc(rffi.CCHARP.TO, self.BUFFER_SIZE,
                                    flavor='raw')

    def __del__(self):
        lltype.free(self.buffer, flavor='raw')
        try:
            self.do_close()
        except OSError:
            pass

    # Abstract methods
    def do_close(self):
        raise NotImplementedError
    def is_valid(self):
        return False
    def do_send_string(self, space, buffer, offset, size):
        raise NotImplementedError
    def do_recv_string(self, space, buflength, maxlength):
        raise NotImplementedError

    def close(self):
        self.do_close()

    def closed_get(self, space):
        return space.newbool(not self.is_valid())
    def readable_get(self, space):
        return space.newbool(bool(self.flags & READABLE))
    def writable_get(self, space):
        return space.newbool(bool(self.flags & WRITABLE))

    def _check_readable(self, space):
        if not self.flags & READABLE:
            raise OperationError(space.w_IOError,
                                 space.wrap("connection is write-only"))
    def _check_writable(self, space):
        if not self.flags & WRITABLE:
            raise OperationError(space.w_IOError,
                                 space.wrap("connection is read-only"))

    @unwrap_spec(buffer='bufferstr', offset='index', size='index')
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

    @unwrap_spec(maxlength='index')
    def recv_bytes(self, space, maxlength=PY_SSIZE_T_MAX):
        self._check_readable(space)
        if maxlength < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("maxlength < 0"))

        res, newbuf = self.do_recv_string(
            space, self.BUFFER_SIZE, maxlength)
        res = intmask(res) # XXX why?
        try:
            if newbuf:
                return space.wrap(rffi.charpsize2str(newbuf, res))
            else:
                return space.wrap(rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

    @unwrap_spec(offset='index')
    def recv_bytes_into(self, space, w_buffer, offset=0):
        rwbuffer = space.rwbuffer_w(w_buffer)
        length = rwbuffer.getlength()

        res, newbuf = self.do_recv_string(
            space, length - offset, PY_SSIZE_T_MAX)
        res = intmask(res) # XXX why?
        try:
            if newbuf:
                raise BufferTooShort(space, space.wrap(
                    rffi.charpsize2str(newbuf, res)))
            rwbuffer.setslice(offset, rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

        return space.wrap(res)

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

    def recv(self, space):
        self._check_readable(space)

        res, newbuf = self.do_recv_string(
            space, self.BUFFER_SIZE, PY_SSIZE_T_MAX)
        res = intmask(res) # XXX why?
        try:
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

    def poll(self, space, w_timeout=0.0):
        self._check_readable(space)
        if space.is_w(w_timeout, space.w_None):
            timeout = -1.0 # block forever
        else:
            timeout = space.float_w(w_timeout)
            if timeout < 0.0:
                timeout = 0.0
        return space.newbool(self.do_poll(space, timeout))

W_BaseConnection.typedef = TypeDef(
    'BaseConnection',
    closed = GetSetProperty(W_BaseConnection.closed_get),
    readable = GetSetProperty(W_BaseConnection.readable_get),
    writable = GetSetProperty(W_BaseConnection.writable_get),

    send_bytes = interp2app(W_BaseConnection.send_bytes),
    recv_bytes = interp2app(W_BaseConnection.recv_bytes),
    recv_bytes_into = interp2app(W_BaseConnection.recv_bytes_into),
    send = interp2app(W_BaseConnection.send),
    recv = interp2app(W_BaseConnection.recv),
    poll = interp2app(W_BaseConnection.poll),
    close = interp2app(W_BaseConnection.close),
    )

class W_FileConnection(W_BaseConnection):
    INVALID_HANDLE_VALUE = -1

    if sys.platform == 'win32':
        def WRITE(self, data):
            from pypy.rlib._rsocket_rffi import send, geterrno
            length = send(self.fd, data, len(data), 0)
            if length < 0:
                raise WindowsError(geterrno(), "send")
            return length
        def READ(self, size):
            from pypy.rlib._rsocket_rffi import socketrecv, geterrno
            with rffi.scoped_alloc_buffer(size) as buf:
                length = socketrecv(self.fd, buf.raw, buf.size, 0)
                if length < 0:
                    raise WindowsError(geterrno(), "recv")
                return buf.str(length)
        def CLOSE(self):
            from pypy.rlib._rsocket_rffi import socketclose
            socketclose(self.fd)
    else:
        def WRITE(self, data):
            import os
            return os.write(self.fd, data)
        def READ(self, length):
            import os
            return os.read(self.fd, length)
        def CLOSE(self):
            import os
            try:
                os.close(self.fd)
            except OSError:
                pass

    def __init__(self, fd, flags):
        W_BaseConnection.__init__(self, flags)
        self.fd = fd

    @unwrap_spec(fd=int, readable=bool, writable=bool)
    def descr_new_file(space, w_subtype, fd, readable=True, writable=True):
        flags = (readable and READABLE) | (writable and WRITABLE)

        self = space.allocate_instance(W_FileConnection, w_subtype)
        W_FileConnection.__init__(self, fd, flags)
        return space.wrap(self)

    def fileno(self, space):
        return space.wrap(self.fd)

    def is_valid(self):
        return self.fd != self.INVALID_HANDLE_VALUE

    def do_close(self):
        if self.is_valid():
            self.CLOSE()
            self.fd = self.INVALID_HANDLE_VALUE

    def do_send_string(self, space, buffer, offset, size):
        # Since str2charp copies the buffer anyway, always combine the
        # "header" and the "body" of the message and send them at once.
        message = lltype.malloc(rffi.CCHARP.TO, size + 4, flavor='raw')
        try:
            rffi.cast(rffi.UINTP, message)[0] = rffi.r_uint(size) # XXX htonl!
            i = size - 1
            while i >= 0:
                message[4 + i] = buffer[offset + i]
                i -= 1
            self._sendall(space, message, size + 4)
        finally:
            lltype.free(message, flavor='raw')

    def do_recv_string(self, space, buflength, maxlength):
        with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1) as length_ptr:
            self._recvall(space, rffi.cast(rffi.CCHARP, length_ptr), 4)
            length = intmask(length_ptr[0])
        if length > maxlength: # bad message, close connection
            self.flags &= ~READABLE
            if self.flags == 0:
                self.close()
            raise OperationError(space.w_IOError, space.wrap(
                "bad message length"))

        if length <= buflength:
            self._recvall(space, self.buffer, length)
            return length, lltype.nullptr(rffi.CCHARP.TO)
        else:
            newbuf = lltype.malloc(rffi.CCHARP.TO, length, flavor='raw')
            self._recvall(space, newbuf, length)
            return length, newbuf

    def _sendall(self, space, message, size):
        while size > 0:
            # XXX inefficient
            data = rffi.charpsize2str(message, size)
            try:
                count = self.WRITE(data)
            except OSError, e:
                raise wrap_oserror(space, e)
            size -= count
            message = rffi.ptradd(message, count)

    def _recvall(self, space, buffer, length):
        length = intmask(length)
        remaining = length
        while remaining > 0:
            try:
                data = self.READ(remaining)
            except OSError, e:
                raise wrap_oserror(space, e)
            count = len(data)
            if count == 0:
                if remaining == length:
                    raise OperationError(space.w_EOFError, space.w_None)
                else:
                    raise OperationError(space.w_IOError, space.wrap(
                        "got end of file during message"))
            # XXX inefficient
            for i in range(count):
                buffer[i] = data[i]
            remaining -= count
            buffer = rffi.ptradd(buffer, count)

    if sys.platform == 'win32':
        def _check_fd(self):
            return self.fd >= 0
    else:
        def _check_fd(self):
            return self.fd >= 0 and self.fd < rpoll.FD_SETSIZE

    def do_poll(self, space, timeout):
        if not self._check_fd():
            raise OperationError(space.w_IOError, space.wrap(
                "handle out of range in select()"))

        r, w, e = rpoll.select([self.fd], [], [], timeout)
        if r:
            return True
        else:
            return False

W_FileConnection.typedef = TypeDef(
    'Connection', W_BaseConnection.typedef,
    __new__ = interp2app(W_FileConnection.descr_new_file.im_func),
    __module__ = '_multiprocessing',
    fileno = interp2app(W_FileConnection.fileno),
)

class W_PipeConnection(W_BaseConnection):
    if sys.platform == 'win32':
        from pypy.rlib.rwin32 import INVALID_HANDLE_VALUE

    def __init__(self, handle, flags):
        W_BaseConnection.__init__(self, flags)
        self.handle = handle

    @unwrap_spec(readable=bool, writable=bool)
    def descr_new_pipe(space, w_subtype, w_handle, readable=True, writable=True):
        from pypy.module._multiprocessing.interp_win32 import handle_w
        handle = handle_w(space, w_handle)
        flags = (readable and READABLE) | (writable and WRITABLE)

        self = space.allocate_instance(W_PipeConnection, w_subtype)
        W_PipeConnection.__init__(self, handle, flags)
        return space.wrap(self)

    def descr_repr(self, space):
        conn_type = ["read-only", "write-only", "read-write"][self.flags]

        return space.wrap("<%s %s, handle %zd>" % (
            conn_type, space.type(self).getname(space), self.do_fileno()))

    def is_valid(self):
        return self.handle != self.INVALID_HANDLE_VALUE

    def fileno(self, space):
        return w_handle(space, self.handle)

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
                raise operationerrfmt(
                    space.w_ValueError,
                    "Cannot send %d bytes over connection", size)
        finally:
            rffi.free_charp(charp)
            lltype.free(written_ptr, flavor='raw')

    def do_recv_string(self, space, buflength, maxlength):
        from pypy.module._multiprocessing.interp_win32 import (
            _ReadFile, _PeekNamedPipe, ERROR_BROKEN_PIPE, ERROR_MORE_DATA)
        from pypy.rlib import rwin32
        from pypy.interpreter.error import wrap_windowserror

        read_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                 flavor='raw')
        left_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                 flavor='raw')
        try:
            result = _ReadFile(self.handle,
                               self.buffer, min(self.BUFFER_SIZE, buflength),
                               read_ptr, rffi.NULL)
            if result:
                return read_ptr[0], lltype.nullptr(rffi.CCHARP.TO)

            err = rwin32.GetLastError()
            if err == ERROR_BROKEN_PIPE:
                raise OperationError(space.w_EOFError, space.w_None)
            elif err != ERROR_MORE_DATA:
                raise wrap_windowserror(space, WindowsError(err, "_ReadFile"))

            # More data...
            if not _PeekNamedPipe(self.handle, rffi.NULL, 0,
                                  lltype.nullptr(rwin32.LPDWORD.TO),
                                  lltype.nullptr(rwin32.LPDWORD.TO),
                                  left_ptr):
                raise wrap_windowserror(space, rwin32.lastWindowsError())

            length = intmask(read_ptr[0] + left_ptr[0])
            if length > maxlength: # bad message, close connection
                self.flags &= ~READABLE
                if self.flags == 0:
                    self.close()
                raise OperationError(space.w_IOError, space.wrap(
                    "bad message length"))

            newbuf = lltype.malloc(rffi.CCHARP.TO, length + 1, flavor='raw')
            for i in range(read_ptr[0]):
                newbuf[i] = self.buffer[i]

            result = _ReadFile(self.handle,
                               rffi.ptradd(newbuf, read_ptr[0]), left_ptr[0],
                               read_ptr, rffi.NULL)
            if not result:
                rffi.free_charp(newbuf)
                raise wrap_windowserror(space, rwin32.lastWindowsError())

            assert read_ptr[0] == left_ptr[0]
            return length, newbuf
        finally:
            lltype.free(read_ptr, flavor='raw')
            lltype.free(left_ptr, flavor='raw')

    def do_poll(self, space, timeout):
        from pypy.module._multiprocessing.interp_win32 import (
            _PeekNamedPipe, _GetTickCount, _Sleep)
        from pypy.rlib import rwin32
        from pypy.interpreter.error import wrap_windowserror
        bytes_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                 flavor='raw')
        try:
            if not _PeekNamedPipe(self.handle, rffi.NULL, 0,
                                  lltype.nullptr(rwin32.LPDWORD.TO),
                                  bytes_ptr,
                                  lltype.nullptr(rwin32.LPDWORD.TO)):
                raise wrap_windowserror(space, rwin32.lastWindowsError())
            bytes = bytes_ptr[0]
        finally:
            lltype.free(bytes_ptr, flavor='raw')

        if timeout == 0.0:
            return bytes > 0

        block = timeout < 0
        if not block:
            # XXX does not check for overflow
            deadline = _GetTickCount() + int(1000 * timeout + 0.5)
        else:
            deadline = 0

        _Sleep(0)

        delay = 1
        while True:
            bytes_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                     flavor='raw')
            try:
                if not _PeekNamedPipe(self.handle, rffi.NULL, 0,
                                      lltype.nullptr(rwin32.LPDWORD.TO),
                                      bytes_ptr,
                                      lltype.nullptr(rwin32.LPDWORD.TO)):
                    raise wrap_windowserror(space, rwin32.lastWindowsError())
                bytes = bytes_ptr[0]
            finally:
                lltype.free(bytes_ptr, flavor='raw')

            if bytes > 0:
                return True

            if not block:
                now = _GetTickCount()
                if now > deadline:
                    return False
                diff = deadline - now
                if delay > diff:
                    delay = diff
            else:
                delay += 1

            if delay >= 20:
                delay = 20
            _Sleep(delay)

            # check for signals
            # PyErr_CheckSignals()

if sys.platform == 'win32':
    W_PipeConnection.typedef = TypeDef(
        'PipeConnection', W_BaseConnection.typedef,
        __new__ = interp2app(W_PipeConnection.descr_new_pipe.im_func),
        __module__ = '_multiprocessing',
        fileno = interp2app(W_PipeConnection.fileno),
    )
