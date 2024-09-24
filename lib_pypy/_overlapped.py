"""
Support routines for overlapping io.
Currently, this extension module is only required when using the
modules on Windows. It is used in asyncio
"""

import sys
from enum import Enum
import _winapi
from _winapi import _Z, RaiseFromWindowsErr

if sys.platform != 'win32':
    raise ModuleNotFoundError("The '_overlapped' module is only available on Windows", name='_overlapped')

# Declare external Win32 functions

if sys.maxsize > 2 ** 31:
    from _pypy_winbase_cffi64 import ffi as _ffi
else:
    from _pypy_winbase_cffi import ffi as _ffi
_kernel32 = _ffi.dlopen('kernel32')

_winsock2 = _ffi.dlopen('Ws2_32')

_mswsock = _ffi.dlopen('Mswsock')

GetVersion = _kernel32.GetVersion
NULL = _ffi.NULL

# Copy values into this namespace for exporting
from _winapi import (  # noqa: F401
    ERROR_IO_PENDING,
    ERROR_NETNAME_DELETED,
    ERROR_OPERATION_ABORTED,
    ERROR_SEM_TIMEOUT,
    ERROR_PIPE_BUSY,
    INFINITE,
    INVALID_HANDLE_VALUE,
)

TF_REUSE_SOCKET = 0x02
SO_UPDATE_ACCEPT_CONTEXT = 0x700B
SO_UPDATE_CONNECT_CONTEXT = 0x7010
SOCKET_ERROR = -1

AF_INET = 2
AF_INET6 = 23

SOCK_STREAM = 1
IPPROTO_TCP = 6

INVALID_SOCKET = -1

IOC_OUT = 0x40000000
IOC_IN = 0x80000000
IOC_INOUT = IOC_IN | IOC_OUT
IOC_WS2 = 0x08000000


def _WSAIORW(x, y):
    return IOC_INOUT | x | y

# from MSWSock.h

WSAID_ACCEPTEX = _ffi.new("GUID[1]")
WSAID_ACCEPTEX[0].Data1 = 0xb5367df1
WSAID_ACCEPTEX[0].Data2 = 0xcbac
WSAID_ACCEPTEX[0].Data3 = 0x11cf
WSAID_ACCEPTEX[0].Data4 = [0x95, 0xca, 0x00, 0x80, 0x5f, 0x48, 0xa1, 0x92]

WSAID_CONNECTEX = _ffi.new("GUID[1]")
WSAID_CONNECTEX[0].Data1 = 0x25a207b9
WSAID_CONNECTEX[0].Data2 = 0xddf3
WSAID_CONNECTEX[0].Data3 = 0x4660
WSAID_CONNECTEX[0].Data4 = [0x8e, 0xe9, 0x76, 0xe5, 0x8c, 0x74, 0x06, 0x3e]

WSAID_DISCONNECTEX = _ffi.new("GUID[1]")
WSAID_DISCONNECTEX[0].Data1 = 0x7fda2e11
WSAID_DISCONNECTEX[0].Data2 = 0x8630
WSAID_DISCONNECTEX[0].Data3 = 0x436f
WSAID_DISCONNECTEX[0].Data4 = [0xa0, 0x31, 0xf5, 0x36, 0xa6, 0xee, 0xc1, 0x57]

WSAID_TRANSMITFILE = _ffi.new("GUID[1]")
WSAID_TRANSMITFILE[0].Data1 = 0xb5367df0
WSAID_TRANSMITFILE[0].Data2 = 0xcbac
WSAID_TRANSMITFILE[0].Data3 = 0x11cf
WSAID_TRANSMITFILE[0].Data4 = [0x95, 0xca, 0x00, 0x80, 0x5f, 0x48, 0xa1, 0x92]

SIO_GET_EXTENSION_FUNCTION_POINTER = _WSAIORW(IOC_WS2, 6)
INADDR_ANY = 0x00000000
STATUS_PENDING = 0x00000103

in6addr_any = _ffi.new("struct in6_addr[1]")
_accept_ex = _ffi.new("AcceptExPtr*")
_connect_ex = _ffi.new("ConnectExPtr*")
_disconnect_ex = _ffi.new("DisconnectExPtr*")
_transmitfile = _ffi.new("TransmitFilePtr*")


def _int2intptr(int2cast):
    return _ffi.cast("ULONG_PTR", int2cast)


def _int2dword(int2cast):
    return _ffi.cast("DWORD", int2cast)


def _int2handle(val):
    return _ffi.cast("HANDLE", val)


def _int2overlappedptr(val):
    return _ffi.cast("OVERLAPPED*", val)


def _handle2int(handle):
    return int(_ffi.cast("intptr_t", handle))


class OverlappedType(Enum):
    TYPE_NONE = 0
    TYPE_NOT_STARTED = 1
    TYPE_READ = 2
    TYPE_READINTO = 3
    TYPE_WRITE = 4
    TYPE_ACCEPT = 5
    TYPE_CONNECT = 6
    TYPE_DISCONNECT = 7
    TYPE_CONNECT_NAMED_PIPE = 8
    TYPE_WAIT_NAMED_PIPE_AND_CONNECT = 9
    TYPE_TRANSMIT_FILE = 10
    TYPE_READ_FROM = 11
    TYPE_WRITE_TO = 12


def initiailize_function_ptrs():
    # importing socket ensures that WSAStartup() is called
    import _socket  # noqa: F401
    s = _winsock2.socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
    dwBytes = _ffi.new("DWORD[1]", [0])
    if s == INVALID_SOCKET:
        _winapi.raise_WinError()

    result = _winsock2.WSAIoctl(
                s,
                SIO_GET_EXTENSION_FUNCTION_POINTER,
                WSAID_ACCEPTEX,
                _ffi.sizeof(WSAID_ACCEPTEX[0]),
                _accept_ex,
                _ffi.sizeof(_accept_ex[0]),
                dwBytes,
                _ffi.NULL,
                _ffi.NULL)
    if result == INVALID_SOCKET:
        _winsock2.closesocket(s)
        _winapi.raise_WinError()

    result = _winsock2.WSAIoctl(
                s,
                SIO_GET_EXTENSION_FUNCTION_POINTER,
                WSAID_CONNECTEX,
                _ffi.sizeof(WSAID_CONNECTEX[0]),
                _connect_ex,
                _ffi.sizeof(_connect_ex[0]),
                dwBytes,
                _ffi.NULL,
                _ffi.NULL)
    if result == INVALID_SOCKET:
        _winsock2.closesocket(s)
        _winapi.raise_WinError()

    result = _winsock2.WSAIoctl(
                s,
                SIO_GET_EXTENSION_FUNCTION_POINTER,
                WSAID_TRANSMITFILE,
                _ffi.sizeof(WSAID_TRANSMITFILE[0]),
                _transmitfile,
                _ffi.sizeof(_transmitfile[0]),
                dwBytes,
                _ffi.NULL,
                _ffi.NULL)
    if result == INVALID_SOCKET:
        _winsock2.closesocket(s)
        _winapi.raise_WinError()

    result = _winsock2.WSAIoctl(
                s,
                SIO_GET_EXTENSION_FUNCTION_POINTER,
                WSAID_DISCONNECTEX,
                _ffi.sizeof(WSAID_DISCONNECTEX[0]),
                _disconnect_ex,
                _ffi.sizeof(_disconnect_ex[0]),
                dwBytes,
                _ffi.NULL,
                _ffi.NULL)

    _winsock2.closesocket(s)
    if result == INVALID_SOCKET:
        _winapi.raise_WinError()


initiailize_function_ptrs()

# This is the class used in asyncio. It is different than the one used
# in multiprocessing, which is in _winapi. See
# https://github.com/python/cpython/issues/64613 for a tiny discussion of
# merging the two

class Overlapped(object):
    def __init__(self, event=_ffi.NULL):
        self.overlapped = _ffi.new('OVERLAPPED[1]')
        self.handle = _ffi.NULL
        self.read_buffer = None
        self.write_buffer = None
        self.error = 0

        self.type = OverlappedType.TYPE_NONE
        if event == _int2handle(INVALID_HANDLE_VALUE) or not event:
            event = _kernel32.CreateEventW(NULL, True, False, NULL)
            if event == _winapi.NULL:
                _winapi.raise_WinError()

        if event:
            self.overlapped[0].hEvent = event
        else:
            _winapi.raise_WinError()

        if self.overlapped[0].hEvent == _ffi.NULL:
            _winapi.raise_WinError()

    def __del__(self):
        olderr = _kernel32.GetLastError()
        hascompletedio = HasOverlappedIoCompleted(self.overlapped[0])
        if not hascompletedio and self.type != OverlappedType.TYPE_NOT_STARTED:
            wait = _kernel32.CancelIoEx(self.handle, self.overlapped)
            ret = self.GetOverlappedResult(wait)
            err = _winapi.ERROR_SUCCESS
            if not ret:
                err = _kernel32.GetLastError()
                self.error = err
            if err != _winapi.ERROR_SUCCESS and \
               err != _winapi.ERROR_NOT_FOUND and \
               err != _winapi.ERROR_OPERATION_ABORTED:
                RaiseFromWindowsErr(err)
        if self.overlapped[0].hEvent != 0:
            _winapi.CloseHandle(self.overlapped[0].hEvent)
        _winapi.SetLastError(olderr)

    @property
    def event(self):
        return self.overlapped[0].hEvent

    def GetOverlappedResult(self, wait):
        transferred = _ffi.new('DWORD[1]', [0])

        if self.type == OverlappedType.TYPE_NONE:
            return _ffi.NULL

        if self.type == OverlappedType.TYPE_NOT_STARTED:
            return _ffi.NULL

        res = _kernel32.GetOverlappedResult(self.handle, self.overlapped,
                                            transferred, wait != 0)
        if res:
            err = _winapi.ERROR_SUCCESS
        else:
            err = _kernel32.GetLastError()
            self.error = err

        if err != _winapi.ERROR_SUCCESS and err != _winapi.ERROR_MORE_DATA:
            if not (err == _winapi.ERROR_BROKEN_PIPE and
                    (self.type in [OverlappedType.TYPE_READ,
                                   OverlappedType.TYPE_READINTO])):
                RaiseFromWindowsErr(err)

        if self.type == OverlappedType.TYPE_READ:
            return _ffi.unpack(self.read_buffer, transferred[0])
        else:
            return transferred[0]

    def cancel(self):
        result = True
        if (self.type == OverlappedType.TYPE_NOT_STARTED or
                self.type == OverlappedType.TYPE_WAIT_NAMED_PIPE_AND_CONNECT):
            return None
        if not HasOverlappedIoCompleted(self.overlapped[0]):
            result = _kernel32.CancelIoEx(self.handle, self.overlapped)
        if (not result and
                _kernel32.GetLastError() != _winapi.ERROR_NOT_FOUND):
            RaiseFromWindowsErr(0)

    def WSARecv(self, handle, size, flags):
        """Start overlapped receive."""
        flags = _int2dword(flags)
        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")

        self.type = OverlappedType.TYPE_READ
        self.handle = _int2handle(handle)
        self.read_buffer = _ffi.new("CHAR[]", max(1, size))
        return self.do_WSARecv(self.handle, self.read_buffer, size, flags)

    def WSARecvInto(self, handle, bufobj, flags):
        """Start overlapped receive."""
        flags = _int2dword(flags)
        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")
        size = len(bufobj)
        self.type = OverlappedType.TYPE_READINTO
        self.handle = _int2handle(handle)
        try:
            self.read_buffer = _ffi.from_buffer(bufobj)
        except Exception as e:
            raise TypeError("bytearray expected in WSARecvInto") from e
        return self.do_WSARecv(self.handle, self.read_buffer, size, flags)

    def WSARecvFrom(self, handle, size, flags=0, /):
        """Start overlapped receive."""
        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")
        self.type = OverlappedType.TYPE_READ_FROM
        self.read_buffer = _ffi.new("CHAR[]", max(1, size))
        self.handle = _int2handle(handle)
        address = _ffi.new("struct sockaddr_in6*")
        length = _ffi.sizeof("struct sockaddr_in6")
        wsabuff = _ffi.new("WSABUF[1]")
        wsabuff[0].len = size
        wsabuff[0].buf = self.read_buffer
        nread = _ffi.new("LPDWORD")
        pflags = _ffi.new("LPDWORD")
        pflags[0] = flags
        lpFromLen = _ffi.new("LPINT")
        lpFromLen[0] = 0
        result = _winsock2.WSARecvFrom(self.handle, wsabuff, _int2dword(1),
                                    nread, pflags, _ffi.NULL, lpFromLen,
                                    self.overlapped, _ffi.NULL)
        if result == SOCKET_ERROR:
            self.error = _winsock2.WSAGetLastError()
        else:
            self.error = _winapi.ERROR_SUCCESS

        if self.error == _winapi.ERROR_BROKEN_PIPE:
            mark_as_completed(self.overlapped)
            RaiseFromWindowsErr(self.error)
        elif self.error in [_winapi.ERROR_SUCCESS, _winapi.ERROR_MORE_DATA,
                            _winapi.ERROR_IO_PENDING]:
            return None
        else:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(self.error)

    def do_WSARecv(self, handle, allocatedbuffer, size, flags):
        nread = _ffi.new("LPDWORD")
        wsabuff = _ffi.new("WSABUF[1]")
        pflags = _ffi.new("LPDWORD")
        pflags[0] = flags

        wsabuff[0].len = size
        wsabuff[0].buf = allocatedbuffer

        result = _winsock2.WSARecv(handle, wsabuff, _int2dword(1), nread,
                                   pflags, self.overlapped, _ffi.NULL)
        if result == SOCKET_ERROR:
            self.error = _winsock2.WSAGetLastError()
        else:
            self.error = _winapi.ERROR_SUCCESS

        if self.error == _winapi.ERROR_BROKEN_PIPE:
            mark_as_completed(self.overlapped)
            RaiseFromWindowsErr(self.error)
        elif self.error in [_winapi.ERROR_SUCCESS, _winapi.ERROR_MORE_DATA,
                            _winapi.ERROR_IO_PENDING]:
            return None
        else:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(self.error)

    def WSASend(self, handle, bufobj, flags):
        """ Send bufobj using handle. Raises on error. Returns None
        """
        handle = _int2handle(handle)

        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")
        self.write_buffer = bytes(bufobj)
        self.type = OverlappedType.TYPE_WRITE
        self.handle = handle

        wsabuff = _ffi.new("WSABUF[1]")
        lgt = len(self.write_buffer)
        wsabuff[0].len = lgt
        # Keep contents alive until WSASend is complete
        contents = _ffi.new('CHAR[]', self.write_buffer)
        wsabuff[0].buf = contents
        nwritten = _ffi.new("LPDWORD")

        result = _winsock2.WSASend(handle, wsabuff, _int2dword(1), nwritten,
                                   flags, self.overlapped, _ffi.NULL)

        if result == SOCKET_ERROR:
            self.error = _winsock2.WSAGetLastError()
        else:
            self.error = _winapi.ERROR_SUCCESS

        if self.error not in [_winapi.ERROR_SUCCESS, _winapi.ERROR_IO_PENDING]:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(self.error)

    def WSASendTo(self, handle, bufobj, flags, AddressObj):
        """ Start overlapped sendto over a connectionless (UDP) socket.
        """
        handle = _int2handle(handle)

        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")
        Length = _ffi.sizeof("struct sockaddr_in6")
        AddressBuf = _ffi.new("CHAR[]", Length)
        Address = _ffi.cast("SOCKADDR *", AddressBuf)
        Address, Length = parse_address(AddressObj, Address, Length)
        if Length < 0:
            return
        self.write_buffer = bytes(bufobj)
        self.type = OverlappedType.TYPE_WRITE_TO
        self.handle = handle

        wsabuff = _ffi.new("WSABUF[1]")
        lgt = len(self.write_buffer)
        wsabuff[0].len = lgt
        # Keep contents alive until WSASend is complete
        contents = _ffi.new('CHAR[]', self.write_buffer)
        wsabuff[0].buf = contents
        nwritten = _ffi.new("LPDWORD")

        result = _winsock2.WSASendTo(handle, wsabuff, _int2dword(1), nwritten,
                                   flags, Address, AddressLength, self.overlapped, _ffi.NULL)

        if result == SOCKET_ERROR:
            self.error = _winsock2.WSAGetLastError()
        else:
            self.error = _winapi.ERROR_SUCCESS

        if self.error not in [_winapi.ERROR_SUCCESS, _winapi.ERROR_IO_PENDING]:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(self.error)

    def getresult(self, wait=False):
        return self.GetOverlappedResult(wait)

    def ConnectNamedPipe(self, handle):
        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")
        self.type = OverlappedType.TYPE_CONNECT_NAMED_PIPE
        self.handle = _int2handle(handle)
        success = _kernel32.ConnectNamedPipe(self.handle, self.overlapped)

        if success:
            err = _winapi.ERROR_SUCCESS
        else:
            err = _kernel32.GetLastError()
            self.error = err

        if err == _winapi.ERROR_IO_PENDING | _winapi.ERROR_SUCCESS:
            return False
        elif err == _winapi.ERROR_PIPE_CONNECTED:
            mark_as_completed(self.overlapped)
            return True
        else:
            RaiseFromWindowsErr(err)

    def ReadFile(self, handle, size):
        self.type = OverlappedType.TYPE_READ
        self.handle = _int2handle(handle)
        self.read_buffer = _ffi.new("CHAR[]", max(1, size))
        return self.do_ReadFile(self.handle, self.read_buffer, size)

    def ReadFileInto(self, handle, bufobj):
        handle = _int2handle(handle)
        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")
        if not isinstance(bufobj, bytearray):
            raise TypeError("bytearray expected in ReadFileInto")
        size = len(bufobj)
        self.type = OverlappedType.TYPE_READINTO
        self.handle = handle
        self.read_buffer = _ffi.from_buffer(bufobj)
        return self.do_ReadFile(handle, self.read_buffer, size)

    def do_ReadFile(self, handle, buf, size):
        nread = _ffi.new('DWORD[1]', [0])
        ret = _kernel32.ReadFile(handle, buf, size, nread, self.overlapped)
        if ret:
            err = _winapi.ERROR_SUCCESS
        else:
            err = _kernel32.GetLastError()

        self.error = err

        if err == _winapi.ERROR_BROKEN_PIPE:
            mark_as_completed(self.overlapped)
            RaiseFromWindowsErr(err)
        elif err in [_winapi.ERROR_SUCCESS, _winapi.ERROR_MORE_DATA,
                     _winapi.ERROR_IO_PENDING]:
            return None
        else:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(err)

    def WriteFile(self, handle, buffer):
        self.handle = _int2handle(handle)
        self.write_buffer = buffer
        written = _ffi.new('DWORD[1]', [0])

        # Check if we have already performed some IO
        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")

        self.type = OverlappedType.TYPE_WRITE

        ret = _kernel32.WriteFile(self.handle, self.write_buffer,
                                  len(self.write_buffer), written,
                                  self.overlapped)

        if ret:
            self.error = _winapi.ERROR_SUCCESS
        else:
            self.error = _kernel32.GetLastError()

        if self.error in (_winapi.ERROR_SUCCESS, _winapi.ERROR_IO_PENDING):
            return None
        else:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(self.error)

    def AcceptEx(self, listensocket, acceptsocket):
        listensocket = _int2handle(listensocket)
        acceptsocket = _int2handle(acceptsocket)
        bytesreceived = _ffi.new("DWORD[1]")

        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")

        size = _ffi.sizeof("struct sockaddr_in6") + 16
        buf = _ffi.new("CHAR[]", size*2)
        if not buf:
            return None

        self.type = OverlappedType.TYPE_ACCEPT
        self.handle = listensocket
        self.read_buffer = buf

        res = _accept_ex[0](listensocket, acceptsocket, buf, 0, size, size,
                            bytesreceived, self.overlapped)

        if res:
            self.error = _winapi.ERROR_SUCCESS
        else:
            self.error = _kernel32.GetLastError()

        if self.error in (_winapi.ERROR_SUCCESS, _winapi.ERROR_IO_PENDING):
            return None
        else:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(0)

    def DisconnectEx(self, socket, flags):
        raise NotImplementedError('not implemented')
        return None

    def TransmitFile(self, Socket, File, offset, offset_high, count_to_write,
                     count_per_send, flags):
        """Transmit file data over a connected socket."""
        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")
        self.type = OverlappedType.TYPE_TRANSMIT_FILE
        self.handle = s = _int2handle(Socket)
        # hmm, there must be a better way to declare these fields
        self.overlapped[0].DUMMYUNIONNAME.DUMMYSTRUCTNAME.Offset = offset
        self.overlapped[0].DUMMYUNIONNAME.DUMMYSTRUCTNAME.OffsetHigh = offset_high
        f = _int2handle(File)
        ret = _transmitfile[0](s, f, count_to_write, count_per_send,
                               self.overlapped, _ffi.NULL, flags);
        if ret == _winapi.ERROR_SUCCESS:
           self.error = ret
        else:
            self.error = _winsock2.WSAGetLastError()
        if self.error in (_winapi.ERROR_SUCCESS, _winapi.ERROR_IO_PENDING):
            return None
        RaiseFromWindowsErr(self.err)

    def ConnectEx(self, socket, addressobj):
        socket = _int2handle(socket)

        if self.type != OverlappedType.TYPE_NONE:
            raise ValueError("operation already attempted")

        address = _ffi.new("struct sockaddr_in6*")
        length = _ffi.sizeof("struct sockaddr_in6")

        address, length = parse_address(addressobj,
                                        _ffi.cast("SOCKADDR*", address),
                                        length)

        if length < 0:
            return None

        self.type = OverlappedType.TYPE_CONNECT
        self.handle = socket

        res = _connect_ex[0](socket, address, length, _ffi.NULL, 0, _ffi.NULL,
                             self.overlapped)

        if res:
            self.error = _winapi.ERROR_SUCCESS
        else:
            self.error = _kernel32.GetLastError()

        if self.error in (_winapi.ERROR_SUCCESS, _winapi.ERROR_IO_PENDING):
            return None
        else:
            self.type = OverlappedType.TYPE_NOT_STARTED
            RaiseFromWindowsErr(0)

    @property
    def pending(self):
        return (not HasOverlappedIoCompleted(self.overlapped[0]) and
                self.type != OverlappedType.TYPE_NOT_STARTED)

    @property
    def address(self):
        return _handle2int(self.overlapped)


def SetEvent(handle):
    ret = _kernel32.SetEvent(_int2handle(handle))
    if not ret:
        _winapi.raise_WinError()


def mark_as_completed(overlapped):
    overlapped[0].Internal = 0
    if overlapped[0].hEvent != _ffi.NULL:
        SetEvent(overlapped[0].hEvent)


def CreateEvent(eventattributes, manualreset, initialstate, name):
    event = _kernel32.CreateEventW(NULL, manualreset, initialstate, _Z(name))
    event = _handle2int(event)
    if not event:
        _winapi.raise_WinError()
    return event


def CreateIoCompletionPort(handle, existingcompletionport, completionkey,
                           numberofconcurrentthreads):
    completionkey = _int2intptr(completionkey)
    existingcompletionport = _int2handle(existingcompletionport)
    numberofconcurrentthreads = _int2dword(numberofconcurrentthreads)
    handle = _int2handle(handle)
    result = _kernel32.CreateIoCompletionPort(handle,
                                              existingcompletionport,
                                              completionkey,
                                              numberofconcurrentthreads)
    if result == _ffi.NULL:
        RaiseFromWindowsErr(0)
    return _handle2int(result)


def PostQueuedCompletionStatus(completionport, ms):
    _winapi.raise_WinError()


def GetQueuedCompletionStatus(completionport, milliseconds):
    numberofbytes = _ffi.new('DWORD[1]', [0])
    completionkey = _ffi.new('ULONG**')
    completionport = _int2handle(completionport)

    if completionport is None:
        _winapi.raise_WinError()
    overlapped = _ffi.new("OVERLAPPED**")
    overlapped[0] = _ffi.NULL
    result = _kernel32.GetQueuedCompletionStatus(completionport,
                                                 numberofbytes,
                                                 completionkey,
                                                 overlapped,
                                                 milliseconds)
    if result:
        err = _winapi.ERROR_SUCCESS
    else:
        err = _kernel32.GetLastError()

    if overlapped[0] == _ffi.NULL:
        if err == _winapi.WAIT_TIMEOUT:
            return None
        RaiseFromWindowsErr(err)

    return (err, numberofbytes, _handle2int(completionkey[0]),
            _handle2int(_ffi.addressof(overlapped[0][0])))


@_ffi.callback("void(void*, int)")
def post_to_queue_callback(lpparameter, timerorwaitfired):
    pdata = _ffi.cast("PostCallbackData*", lpparameter)
    _kernel32.PostQueuedCompletionStatus(
                pdata.hCompletionPort,
                timerorwaitfired,
                _ffi.cast("ULONG_PTR", 0),
                pdata.Overlapped,
    )
    _winapi.free(pdata)


def RegisterWaitWithQueue(object, completionport, ovaddress, miliseconds):
    data = _ffi.cast('PostCallbackData*',
                     _winapi.malloc(_ffi.sizeof("PostCallbackData")))
    newwaitobject = _ffi.new("HANDLE*")
    data[0].hCompletionPort = _int2handle(completionport)
    data[0].Overlapped = _int2overlappedptr(ovaddress)
    ret = _kernel32.RegisterWaitForSingleObject(
              newwaitobject,
              _int2handle(object),
              _ffi.cast("WAITORTIMERCALLBACK", post_to_queue_callback),
              data,
              miliseconds,
              _kernel32.WT_EXECUTEINWAITTHREAD | _kernel32.WT_EXECUTEONLYONCE,
          )
    if not ret:
        RaiseFromWindowsErr(0)

    return _handle2int(newwaitobject[0])


def ConnectPipe(address):
    err = _winapi.ERROR_PIPE_BUSY
    waddress = _ffi.new("wchar_t[]", address)
    handle = _kernel32.CreateFileW(
                waddress,
                _winapi.GENERIC_READ | _winapi.GENERIC_WRITE,
                0,
                _ffi.NULL,
                _winapi.OPEN_EXISTING,
                _winapi.FILE_FLAG_OVERLAPPED,
                _ffi.NULL,
             )
    err = _kernel32.GetLastError()

    if handle == INVALID_HANDLE_VALUE or err == _winapi.ERROR_PIPE_BUSY:
        RaiseFromWindowsErr(err)

    return _handle2int(handle)

def WSAConnect(ConnectSocket, AddressObj):
    """Bind a remote address to a connectionless (UDP) socket"""

    Length = _ffi.sizeof("struct sockaddr_in6")
    AddressBuf = _ffi.new("CHAR[]", Length)
    Address = _ffi.cast("SOCKADDR *", AddressBuf)
    Address, Length = parse_address(AddressObj, Address, Length)
    if Length < 0:
        return
    err = _winsock2.WSAConnect(_int2handle(ConnectSocket), Address, Length,
                               _ffi.NULL, _ffi.NULL, _ffi.NULL, _ffi.NULL)
    if err != 0:
        RaiseFromWindowsErr(_winsock2.WSAGetLastError())

def UnregisterWaitEx(handle, event):
    waithandle = _int2handle(handle)
    waitevent = _int2handle(event)

    ret = _kernel32.UnregisterWaitEx(waithandle, waitevent)

    if not ret:
        RaiseFromWindowsErr(0)


def UnregisterWait(handle):
    handle = _int2handle(handle)

    ret = _kernel32.UnregisterWait(handle)

    if not ret:
        RaiseFromWindowsErr(0)


def BindLocal(socket, family):
    socket = _int2handle(socket)
    if family == AF_INET:
        addr = _ffi.new("struct sockaddr_in*")
        addr[0].sin_family = AF_INET
        addr[0].sin_port = 0
        addr[0].sin_addr.S_un.S_addr = INADDR_ANY
        paddr = _ffi.cast("PSOCKADDR", addr)
        result = _winsock2.bind(socket, paddr,
                                _ffi.sizeof("struct sockaddr_in"))
    elif family == AF_INET6:
        addr = _ffi.new("struct sockaddr_in6*")
        addr.sin6_family = AF_INET6
        addr.sin6_port = 0
        addr.sin6_addr = in6addr_any[0]
        result = _winsock2.bind(socket, _ffi.cast("PSOCKADDR", addr),
                                _ffi.sizeof("struct sockaddr_in"))
    else:
        raise ValueError()

    if result == SOCKET_ERROR:
        RaiseFromWindowsErr(0)


def HasOverlappedIoCompleted(overlapped):
    return (overlapped.Internal != STATUS_PENDING)


def parse_address(addressobj, address, length):
    lengthptr = _ffi.new("INT*")
    lengthptr[0] = length
    if len(addressobj) == 2:
        host, port = addressobj
        address[0].sa_family = AF_INET
        result = _winsock2.WSAStringToAddressW(host, AF_INET, _ffi.NULL,
                                               address, lengthptr)
        if result < 0:
            raise _winapi.WinError()
        _ffi.cast("SOCKADDR_IN*", address)[0].sin_port = _winsock2.htons(port)
        return address, lengthptr[0]
    elif len(addressobj) == 4:
        host, port, flowinfo, scopeid = addressobj
        address[0].sa_family = AF_INET6
        result = _winsock2.WSAStringToAddressW(host, AF_INET6, _ffi.NULL,
                                               address, lengthptr)
        if result < 0:
            RaiseFromWindowsErr(_winsock2.WSAGetLastError())
        add6 = _ffi.cast("struct sockaddr_in6 *", address)
        add6[0].sin6_port = _winsock2.htons(port)
        add6[0].sin6_flowinfo = flowinfo
        add6[0].sin6_scope_id = scopeid
        return address, lengthptr[0]
    else:
        return -1
