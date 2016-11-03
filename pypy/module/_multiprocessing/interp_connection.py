import sys
from errno import EINTR

from rpython.rlib import rpoll, rsocket
from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt, wrap_oserror
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.typedef import GetSetProperty, TypeDef

READABLE, WRITABLE = range(1, 3)
PY_SSIZE_T_MAX = sys.maxint
PY_SSIZE_T_MIN = -sys.maxint - 1

class State(object):
    def __init__(self, space):
        pass

    def init(self, space):
        w_builtins = space.getbuiltinmodule('__builtin__')
        w_module = space.call_method(
            w_builtins, '__import__', space.newtext("multiprocessing"))
        self.w_BufferTooShort = space.getattr(w_module, space.newtext("BufferTooShort"))

        self.w_picklemodule = space.call_method(
            w_builtins, '__import__', space.newtext("pickle"))

def BufferTooShort(space, w_data):
    w_BufferTooShort = space.fromcache(State).w_BufferTooShort
    return OperationError(w_BufferTooShort, w_data)

def w_handle(space, handle):
    return space.newint(rffi.cast(rffi.INTPTR_T, handle))


class W_BaseConnection(W_Root):
    BUFFER_SIZE = 1024
    buffer = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, space, flags):
        self.flags = flags
        self.buffer = lltype.malloc(rffi.CCHARP.TO, self.BUFFER_SIZE,
                                    flavor='raw')
        self.register_finalizer(space)

    def _finalize_(self):
        buf = self.buffer
        if buf:
            self.buffer = lltype.nullptr(rffi.CCHARP.TO)
            lltype.free(buf, flavor='raw')
        try:
            self.do_close()
        except OSError:
            pass

    # Abstract methods
    def do_close(self):
        raise NotImplementedError
    def is_valid(self):
        return False
    def do_send_string(self, space, buf, offset, size):
        raise NotImplementedError
    def do_recv_string(self, space, buflength, maxlength):
        raise NotImplementedError
    def do_poll(self, space, timeout):
        raise NotImplementedError

    def close(self):
        self.do_close()

    def closed_get(self, space):
        return space.newbool(not self.is_valid())
    def readable_get(self, space):
        return space.newbool(bool(self.flags & READABLE))
    def writable_get(self, space):
        return space.newbool(bool(self.flags & WRITABLE))

    def _repr(self, space, handle):
        conn_type = ["read-only", "write-only", "read-write"][self.flags - 1]
        return space.newtext("<%s %s, handle %d>" % (
                conn_type, space.type(self).getname(space), handle))

    def descr_repr(self, space):
        raise NotImplementedError

    def _check_readable(self, space):
        if not self.flags & READABLE:
            raise oefmt(space.w_IOError, "connection is write-only")
    def _check_writable(self, space):
        if not self.flags & WRITABLE:
            raise oefmt(space.w_IOError, "connection is read-only")

    @unwrap_spec(offset='index', size='index')
    def send_bytes(self, space, w_buf, offset=0, size=PY_SSIZE_T_MIN):
        buf = space.getarg_w('s*', w_buf).as_str()
        length = len(buf)
        self._check_writable(space)
        if offset < 0:
            raise oefmt(space.w_ValueError, "offset is negative")
        if length < offset:
            raise oefmt(space.w_ValueError, "buffer length < offset")

        if size == PY_SSIZE_T_MIN:
            size = length - offset
        elif size < 0:
            raise oefmt(space.w_ValueError, "size is negative")
        elif offset + size > length:
            raise oefmt(space.w_ValueError, "buffer length > offset + size")

        self.do_send_string(space, buf, offset, size)

    @unwrap_spec(maxlength='index')
    def recv_bytes(self, space, maxlength=PY_SSIZE_T_MAX):
        self._check_readable(space)
        if maxlength < 0:
            raise oefmt(space.w_ValueError, "maxlength < 0")

        res, newbuf = self.do_recv_string(
            space, self.BUFFER_SIZE, maxlength)
        try:
            if newbuf:
                return space.newbytes(rffi.charpsize2str(newbuf, res))
            else:
                return space.newbytes(rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

    @unwrap_spec(offset='index')
    def recv_bytes_into(self, space, w_buffer, offset=0):
        rwbuffer = space.writebuf_w(w_buffer)
        length = rwbuffer.getlength()

        res, newbuf = self.do_recv_string(
            space, length - offset, PY_SSIZE_T_MAX)
        try:
            if newbuf:
                raise BufferTooShort(space, space.newbytes(
                    rffi.charpsize2str(newbuf, res)))
            rwbuffer.setslice(offset, rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

        return space.newint(res)

    def send(self, space, w_obj):
        self._check_writable(space)

        w_picklemodule = space.fromcache(State).w_picklemodule
        w_protocol = space.getattr(
            w_picklemodule, space.newtext("HIGHEST_PROTOCOL"))
        w_pickled = space.call_method(
            w_picklemodule, "dumps", w_obj, w_protocol)

        buf = space.str_w(w_pickled)
        self.do_send_string(space, buf, 0, len(buf))

    def recv(self, space):
        self._check_readable(space)

        res, newbuf = self.do_recv_string(
            space, self.BUFFER_SIZE, PY_SSIZE_T_MAX)
        try:
            if newbuf:
                w_received = space.newbytes(rffi.charpsize2str(newbuf, res))
            else:
                w_received = space.newbytes(rffi.charpsize2str(self.buffer, res))
        finally:
            if newbuf:
                rffi.free_charp(newbuf)

        w_builtins = space.getbuiltinmodule('__builtin__')
        w_picklemodule = space.fromcache(State).w_picklemodule
        w_unpickled = space.call_method(
            w_picklemodule, "loads", w_received)

        return w_unpickled

    @unwrap_spec(w_timeout=WrappedDefault(0.0))
    def poll(self, space, w_timeout):
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
    __repr__ = interpindirect2app(W_BaseConnection.descr_repr),
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
    fd = INVALID_HANDLE_VALUE

    if sys.platform == 'win32':
        def WRITE(self, data):
            from rpython.rlib._rsocket_rffi import send, geterrno
            length = send(self.fd, data, len(data), 0)
            if length < 0:
                raise WindowsError(geterrno(), "send")
            return length
        def READ(self, size):
            from rpython.rlib._rsocket_rffi import socketrecv, geterrno
            with rffi.scoped_alloc_buffer(size) as buf:
                length = socketrecv(self.fd, buf.raw, buf.size, 0)
                if length < 0:
                    raise WindowsError(geterrno(), "recv")
                return buf.str(length)
        def CLOSE(self):
            from rpython.rlib._rsocket_rffi import socketclose
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

    def __init__(self, space, fd, flags):
        if fd == self.INVALID_HANDLE_VALUE or fd < 0:
            raise oefmt(space.w_IOError, "invalid handle %d", fd)
        W_BaseConnection.__init__(self, space, flags)
        self.fd = fd

    @unwrap_spec(fd=int, readable=bool, writable=bool)
    def descr_new_file(space, w_subtype, fd, readable=True, writable=True):
        flags = (readable and READABLE) | (writable and WRITABLE)

        self = space.allocate_instance(W_FileConnection, w_subtype)
        W_FileConnection.__init__(self, space, fd, flags)
        return self

    def descr_repr(self, space):
        return self._repr(space, self.fd)

    def fileno(self, space):
        return space.newint(self.fd)

    def is_valid(self):
        return self.fd != self.INVALID_HANDLE_VALUE

    def do_close(self):
        if self.is_valid():
            self.CLOSE()
            self.fd = self.INVALID_HANDLE_VALUE

    def do_send_string(self, space, buf, offset, size):
        # Since str2charp copies the buf anyway, always combine the
        # "header" and the "body" of the message and send them at once.
        message = lltype.malloc(rffi.CCHARP.TO, size + 4, flavor='raw')
        try:
            length = rffi.r_uint(rsocket.htonl(
                    rffi.cast(lltype.Unsigned, size)))
            rffi.cast(rffi.UINTP, message)[0] = length
            i = size - 1
            while i >= 0:
                message[4 + i] = buf[offset + i]
                i -= 1
            self._sendall(space, message, size + 4)
        finally:
            lltype.free(message, flavor='raw')

    def do_recv_string(self, space, buflength, maxlength):
        with lltype.scoped_alloc(rffi.CArrayPtr(rffi.UINT).TO, 1) as length_ptr:
            self._recvall(space, rffi.cast(rffi.CCHARP, length_ptr), 4)
            length = intmask(rsocket.ntohl(
                    rffi.cast(lltype.Unsigned, length_ptr[0])))
        if length > maxlength: # bad message, close connection
            self.flags &= ~READABLE
            if self.flags == 0:
                self.close()
            raise oefmt(space.w_IOError, "bad message length")

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
            except OSError as e:
                if e.errno == EINTR:
                    space.getexecutioncontext().checksignals()
                    continue
                raise wrap_oserror(space, e)
            size -= count
            message = rffi.ptradd(message, count)

    def _recvall(self, space, buf, length):
        length = intmask(length)
        remaining = length
        while remaining > 0:
            try:
                data = self.READ(remaining)
            except OSError as e:
                if e.errno == EINTR:
                    space.getexecutioncontext().checksignals()
                    continue
                raise wrap_oserror(space, e)
            count = len(data)
            if count == 0:
                if remaining == length:
                    raise OperationError(space.w_EOFError, space.w_None)
                else:
                    raise oefmt(space.w_IOError,
                                "got end of file during message")
            # XXX inefficient
            for i in range(count):
                buf[i] = data[i]
            remaining -= count
            buf = rffi.ptradd(buf, count)

    if sys.platform == 'win32':
        def _check_fd(self):
            return self.fd >= 0
    else:
        def _check_fd(self):
            return self.fd >= 0 and self.fd < rpoll.FD_SETSIZE

    def do_poll(self, space, timeout):
        if not self._check_fd():
            raise oefmt(space.w_IOError, "handle out of range in select()")
        r, w, e = rpoll.select([self.fd], [], [], timeout, handle_eintr=True)
        return bool(r)

W_FileConnection.typedef = TypeDef(
    '_multiprocessing.Connection', W_BaseConnection.typedef,
    __new__ = interp2app(W_FileConnection.descr_new_file.im_func),
    fileno = interp2app(W_FileConnection.fileno),
)

class W_PipeConnection(W_BaseConnection):
    if sys.platform == 'win32':
        from rpython.rlib.rwin32 import INVALID_HANDLE_VALUE

    def __init__(self, space, handle, flags):
        W_BaseConnection.__init__(self, space, flags)
        self.handle = handle

    @unwrap_spec(readable=bool, writable=bool)
    def descr_new_pipe(space, w_subtype, w_handle, readable=True,
                       writable=True):
        from pypy.module._multiprocessing.interp_win32 import handle_w
        handle = handle_w(space, w_handle)
        flags = (readable and READABLE) | (writable and WRITABLE)

        self = space.allocate_instance(W_PipeConnection, w_subtype)
        W_PipeConnection.__init__(self, space, handle, flags)
        return self

    def descr_repr(self, space):
        return self._repr(space, rffi.cast(rffi.INTPTR_T, self.handle))

    def is_valid(self):
        return self.handle != self.INVALID_HANDLE_VALUE

    def fileno(self, space):
        return w_handle(space, self.handle)

    def do_close(self):
        from rpython.rlib.rwin32 import CloseHandle
        if self.is_valid():
            CloseHandle(self.handle)
            self.handle = self.INVALID_HANDLE_VALUE

    def do_send_string(self, space, buf, offset, size):
        from pypy.module._multiprocessing.interp_win32 import (
            _WriteFile, ERROR_NO_SYSTEM_RESOURCES)
        from rpython.rlib import rwin32

        with rffi.scoped_view_charp(buf) as charp:
            written_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                        flavor='raw')
            try:
                result = _WriteFile(
                    self.handle, rffi.ptradd(charp, offset),
                    size, written_ptr, rffi.NULL)

                if (result == 0 and
                    rwin32.GetLastError_saved() == ERROR_NO_SYSTEM_RESOURCES):
                    raise oefmt(space.w_ValueError,
                                "Cannot send %d bytes over connection", size)
            finally:
                lltype.free(written_ptr, flavor='raw')

    def do_recv_string(self, space, buflength, maxlength):
        from pypy.module._multiprocessing.interp_win32 import (
            _ReadFile, _PeekNamedPipe, ERROR_BROKEN_PIPE, ERROR_MORE_DATA)
        from rpython.rlib import rwin32
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
                return intmask(read_ptr[0]), lltype.nullptr(rffi.CCHARP.TO)

            err = rwin32.GetLastError_saved()
            if err == ERROR_BROKEN_PIPE:
                raise OperationError(space.w_EOFError, space.w_None)
            elif err != ERROR_MORE_DATA:
                raise wrap_windowserror(space, WindowsError(err, "_ReadFile"))

            # More data...
            if not _PeekNamedPipe(self.handle, rffi.NULL, 0,
                                  lltype.nullptr(rwin32.LPDWORD.TO),
                                  lltype.nullptr(rwin32.LPDWORD.TO),
                                  left_ptr):
                raise wrap_windowserror(space, rwin32.lastSavedWindowsError())

            length = intmask(read_ptr[0] + left_ptr[0])
            if length > maxlength: # bad message, close connection
                self.flags &= ~READABLE
                if self.flags == 0:
                    self.close()
                raise oefmt(space.w_IOError, "bad message length")

            newbuf = lltype.malloc(rffi.CCHARP.TO, length + 1, flavor='raw')
            for i in range(read_ptr[0]):
                newbuf[i] = self.buffer[i]

            result = _ReadFile(self.handle,
                               rffi.ptradd(newbuf, read_ptr[0]), left_ptr[0],
                               read_ptr, rffi.NULL)
            if not result:
                rffi.free_charp(newbuf)
                raise wrap_windowserror(space, rwin32.lastSavedWindowsError())

            assert read_ptr[0] == left_ptr[0]
            return length, newbuf
        finally:
            lltype.free(read_ptr, flavor='raw')
            lltype.free(left_ptr, flavor='raw')

    def do_poll(self, space, timeout):
        from pypy.module._multiprocessing.interp_win32 import (
            _PeekNamedPipe, _GetTickCount, _Sleep)
        from rpython.rlib import rwin32
        from pypy.interpreter.error import wrap_windowserror
        bytes_ptr = lltype.malloc(rffi.CArrayPtr(rwin32.DWORD).TO, 1,
                                 flavor='raw')
        try:
            if not _PeekNamedPipe(self.handle, rffi.NULL, 0,
                                  lltype.nullptr(rwin32.LPDWORD.TO),
                                  bytes_ptr,
                                  lltype.nullptr(rwin32.LPDWORD.TO)):
                raise wrap_windowserror(space, rwin32.lastSavedWindowsError())
            bytes = bytes_ptr[0]
        finally:
            lltype.free(bytes_ptr, flavor='raw')

        if timeout == 0.0:
            return bytes > 0

        block = timeout < 0
        if not block:
            # XXX does not check for overflow
            deadline = intmask(_GetTickCount()) + int(1000 * timeout + 0.5)
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
                    raise wrap_windowserror(space,
                                            rwin32.lastSavedWindowsError())
                bytes = bytes_ptr[0]
            finally:
                lltype.free(bytes_ptr, flavor='raw')

            if bytes > 0:
                return True

            if not block:
                now = intmask(_GetTickCount())
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
        '_multiprocessing.PipeConnection', W_BaseConnection.typedef,
        __new__ = interp2app(W_PipeConnection.descr_new_pipe.im_func),
        fileno = interp2app(W_PipeConnection.fileno),
    )
