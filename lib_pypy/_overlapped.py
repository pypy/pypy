"""
Support routines for overlapping io.
Currently, this extension module is only required when using the
modules on Windows.
"""

import sys
if sys.platform != 'win32':
    raise ImportError("The '_overlapped' module is only available on Windows")

# Declare external Win32 functions

from _pypy_winbase_cffi import ffi as _ffi
_kernel32 = _ffi.dlopen('kernel32')

GetVersion = _kernel32.GetVersion
NULL = _ffi.NULL


from _winapi import INVALID_HANDLE_VALUE, _MAX_PATH , _Z, _int2handle
import _winapi

from enum import Enum
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


class Overlapped(object):
    def __init__(self, handle):
        self.overlapped = _ffi.new('OVERLAPPED[1]')
        self.handle = handle
        self.readbuffer = None
        self.pending = 0
        self.completed = 0
        self.writebuffer = None
        self.type = OverlappedType.TYPE_NONE
        self.overlapped[0].hEvent = \
                _kernel32.CreateEventW(NULL, True, False, NULL)
        self.address = _ffi.addressof(self.overlapped)

    def __del__(self):
        # do this somehow else
        xxx
        err = _kernel32.GetLastError()
        bytes = _ffi.new('DWORD[1]')
        o = overlapped[0]
        if overlapped[0].pending:
            if _kernel32.CancelIoEx(o.handle, o.overlapped) & \
                self.GetOverlappedResult(o.handle, o.overlapped, _ffi.addressof(bytes), True):
                # The operation is no longer pending, nothing to do
                pass
            else:
                raise RuntimeError('deleting an overlapped struct with a pending operation not supported')

    @property
    def event(self):
        return self.overlapped[0].hEvent

    def GetOverlappedResult(self, wait):
        transferred = _ffi.new('DWORD[1]', [0])
        res = _kernel32.GetOverlappedResult(self.handle, self.overlapped, transferred, wait != 0)
        if res:
            err = _winapi.ERROR_SUCCESS
        else:
            err = GetLastError()
        if err in (_winapi.ERROR_SUCCESS, _winapi.ERROR_MORE_DATA, _winapi.ERROR_OPERATION_ABORTED):
            self.completed = 1
            self.pending = 0
        elif res == _winapi.ERROR_IO_INCOMPLETE:
            pass
        else:
            self.pending = 0
            raise _winapi._WinError()
        if self.completed and self.read_buffer:
            if transferred != len(self.read_buffer):
                raise _winapi._WinError()
        return transferred[0], err

    def getbuffer(self):
        xxx
        return None

    def cancel(self):
        result = true
        if self.type == OverlappedType.TYPE_NOT_STARTED or OverlappedType.TYPE_WAIT_NAMED_PIPE_AND_CONNECT:
            return None
        if not _kernel32.HasOverlappedIoCompleted(self.overlapped):
            ### If we are to support xp we will need to dynamically load the below method
            _kernel32.CancelIoEx(self.handle, self.overlapped)        
        return result


def _int2intptr(int2cast):
    return _ffi.cast("ULONG *", int2cast) 

def _int2dword(int2cast):
    return _ffi.new("DWORD[1]", [int2cast])

def CreateEvent(eventattributes, manualreset, initialstate, name):
    event = _kernel32.CreateEventW(NULL, manualreset, initialstate, _Z(name))
    if not event:
        raise _winapi._WinError()
    return event
 
def ConnectNamedPipe(handle, overlapped=False):
    if overlapped:
        ov = Overlapped(handle)
    else:
        ov = Overlapped(None)
    success = _kernel32.ConnectNamedPipe(handle, ov.overlapped)
    if overlapped:
        # Overlapped ConnectNamedPipe never returns a success code
        assert success == 0
        err = _kernel32.GetLastError()
        if err == _winapi.ERROR_IO_PENDING:
            ov.pending = 1
        elif err == _winapi.ERROR_PIPE_CONNECTED:
            _kernel32.SetEvent(ov.overlapped[0].hEvent)
        else:
            del ov
            raise _winapi._WinError()
        return ov
    elif not success:
        raise _winapi._WinError()

def CreateIoCompletionPort(handle, existingcompletionport, completionkey, numberofconcurrentthreads):
    ##completionkey = _int2intptr(completionkey)
    existingcompletionport = _int2handle(existingcompletionport)
    ##numberofconcurrentthreads = _int2dword(numberofconcurrentthreads)

    #import pdb; pdb.set_trace()
    result = _kernel32.CreateIoCompletionPort(handle,
                                              existingcompletionport,
                                              completionkey, 
                                              numberofconcurrentthreads)
    if not result:
        raise _winapi._WinError()
    
    return result

def GetQueuedCompletionStatus(completionport, milliseconds):
    numberofbytes = _ffi.new('DWORD[1]', [0])
    completionkey  = _ffi.new('ULONG *', 0)

    if completionport is None:
        raise _winapi._WinError()
    overlapped = _ffi.new('OVERLAPPED*')
    result = _kernel32.GetQueuedCompletionStatus(completionport, 
                                                 numberofbytes,
                                                 completionkey,
                                                 overlapped,
                                                 milliseconds)
    err = _kernel32.GetLastError()
    return (err, numberofbytes, completionkey, overlapped)

@_ffi.callback("void(void*, bool)")
def post_to_queue_callback(lpparameter, timerorwaitfired):
    pdata = _ffi.cast("PostCallbackData *", lpparameter)
    _kernel32.PostQueuedCompletionStatus(pdata.hCompletionPort, timerorwaitfired, 0, pdata.Overlapped)


def RegisterWaitWithQueue(object, completionport, ovaddress, miliseconds):
    data = _ffi.new('PostCallbackData[1]')
    newwaitobject = _ffi.new("HANDLE[1]")

    data[0].hCompletionPort = completionport
    data[0].Overlapped = ovaddress[0]
    success = _kernel32.RegisterWaitForSingleObject(newwaitobject,
                                                    object,
                                                    _ffi.cast("WAITORTIMERCALLBACK",post_to_queue_callback),
                                                    data,
                                                    miliseconds, 
                                                    _kernel32.WT_EXECUTEINWAITTHREAD | _kernel32.WT_EXECUTEONLYONCE)
    
    return newwaitobject
