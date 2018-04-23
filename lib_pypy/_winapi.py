"""
Support routines for subprocess and multiprocess module.
Currently, this extension module is only required when using the
modules on Windows.
"""

import sys
if sys.platform != 'win32':
    raise ImportError("The '_winapi' module is only available on Windows")

# Declare external Win32 functions

from _pypy_winbase_cffi import ffi as _ffi
_kernel32 = _ffi.dlopen('kernel32')

GetVersion = _kernel32.GetVersion
NULL = _ffi.NULL

# Now the _subprocess module implementation

def _WinError():
    code, message = _ffi.getwinerror()
    raise WindowsError(code, message)

def _int2handle(val):
    return _ffi.cast("HANDLE", val)

def _handle2int(handle):
    return int(_ffi.cast("intptr_t", handle))

_INVALID_HANDLE_VALUE = _int2handle(-1)

def CreatePipe(attributes, size):
    handles = _ffi.new("HANDLE[2]")

    res = _kernel32.CreatePipe(handles, handles + 1, NULL, size)

    if not res:
        raise _WinError()

    return _handle2int(handles[0]), _handle2int(handles[1])

def CreateNamedPipe(*args):
    handle = _kernel32.CreateNamedPipeW(*args)
    if handle == INVALID_HANDLE_VALUE:
        raise _WinError()
    return handle

def CreateFile(*args):
    handle = _kernel32.CreateFileW(*args)
    if handle == INVALID_HANDLE_VALUE:
        raise _WinError()
    return handle

def SetNamedPipeHandleState(namedpipe, mode, max_collection_count, collect_data_timeout):
    d0 = _ffi.new('DWORD[1]', [mode])
    if max_collection_count is None:
        d1 = NULL
    else:
        d1 = _ffi.new('DWORD[1]', [max_collection_count])
    if collect_data_timeout is None:
        d2 = NULL
    else:
        d2 = _ffi.new('DWORD[1]', [collect_data_timeout])
    ret = _kernel32.SetNamedPipeHandleState(namedpipe, d0, d1, d2)
    if not ret:
        raise _WinError()

class Overlapped(object):
    def __init__(self, handle):
        self.overlapped = _ffi.new('OVERLAPPED[1]')
        self.handle = handle
        self.readbuffer = None
        self.pending = 0
        self.completed = 0
        self.writebuffer = None
        self.overlapped[0].hEvent = \
                _kernel32.CreateEventW(NULL, True, False, NULL)

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
                raise RuntimeError('deleting an overlapped strucwith a pending operation not supported')

    @property
    def event(self):
        return None

    def GetOverlappedResult(self, wait):
        transferred = _ffi.new('DWORD[1]', [0])
        res = _kernel32.GetOverlappedResult(self.handle, self.overlapped, transferred, wait != 0)
        if not res:
            res = GetLastError()
        if res in (ERROR_SUCCESS, ERROR_MORE_DATA, ERROR_OPERATION_ABORTED):
            self.completed = 1
            self.pending = 0
        elif res == ERROR_IO_INCOMPLETE:
            pass
        else:
            self.pending = 0
            raise _WinError()
        if self.completed and self.read_buffer:
            if transferred != len(self.read_buffer):
                raise _WinError()
        return transferred[0], err

    def getbuffer(self):
        xxx
        return None

    def cancel(self):
        xxx
        return None

 
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
        if err == ERROR_IO_PENDING:
            overlapped[0].pending = 1
        elif err == ERROR_PIPE_CONNECTED:
            _kernel32.SetEvent(ov.overlapped[0].hEvent)
        else:
            del ov
            raise _WinError()
        return ov
    elif not success:
        raise _WinError()

def GetCurrentProcess():
    return _handle2int(_kernel32.GetCurrentProcess())

def DuplicateHandle(source_process, source, target_process, access, inherit, options=0):
    # CPython: the first three arguments are expected to be integers
    target = _ffi.new("HANDLE[1]")

    res = _kernel32.DuplicateHandle(
        _int2handle(source_process),
        _int2handle(source),
        _int2handle(target_process),
        target, access, inherit, options)

    if not res:
        raise _WinError()

    return _handle2int(target[0])

def _Z(input):
    if input is None:
        return _ffi.NULL
    if isinstance(input, str):
        return input
    raise TypeError("str or None expected, got %r" % (
        type(input).__name__,))

def CreateProcess(name, command_line, process_attr, thread_attr,
                  inherit, flags, env, start_dir, startup_info):
    si = _ffi.new("STARTUPINFO *")
    if startup_info is not None:
        si.dwFlags = startup_info.dwFlags
        si.wShowWindow = startup_info.wShowWindow
        # CPython: these three handles are expected to be
        # subprocess.Handle (int) objects
        if startup_info.hStdInput:
            si.hStdInput = _int2handle(startup_info.hStdInput)
        if startup_info.hStdOutput:
            si.hStdOutput = _int2handle(startup_info.hStdOutput)
        if startup_info.hStdError:
            si.hStdError = _int2handle(startup_info.hStdError)

    pi = _ffi.new("PROCESS_INFORMATION *")
    flags |= CREATE_UNICODE_ENVIRONMENT

    if env is not None:
        envbuf = ""
        for k, v in env.items():
            envbuf += "%s=%s\0" % (k, v)
        envbuf += '\0'
    else:
        envbuf = _ffi.NULL

    res = _kernel32.CreateProcessW(_Z(name), _Z(command_line), _ffi.NULL,
                                   _ffi.NULL, inherit, flags, envbuf,
                                   _Z(start_dir), si, pi)

    if not res:
        raise _WinError()

    return (_handle2int(pi.hProcess),
            _handle2int(pi.hThread),
            pi.dwProcessId,
            pi.dwThreadId)

def WaitForSingleObject(handle, milliseconds):
    # CPython: the first argument is expected to be an integer.
    res = _kernel32.WaitForSingleObject(_int2handle(handle), milliseconds)
    if res < 0:
        raise _WinError()

    return res

def GetExitCodeProcess(handle):
    # CPython: the first argument is expected to be an integer.
    code = _ffi.new("DWORD[1]")

    res = _kernel32.GetExitCodeProcess(_int2handle(handle), code)

    if not res:
        raise _WinError()

    return code[0]

def TerminateProcess(handle, exitcode):
    # CPython: the first argument is expected to be an integer.
    # The second argument is silently wrapped in a UINT.
    res = _kernel32.TerminateProcess(_int2handle(handle),
                                     _ffi.cast("UINT", exitcode))

    if not res:
        raise _WinError()

def GetStdHandle(stdhandle):
    stdhandle = _ffi.cast("DWORD", stdhandle)
    res = _kernel32.GetStdHandle(stdhandle)

    if not res:
        return None
    else:
        return _handle2int(res)

def CloseHandle(handle):
    res = _kernel32.CloseHandle(_int2handle(handle))

    if not res:
        raise _WinError()

def GetModuleFileName(module):
    buf = _ffi.new("wchar_t[]", _MAX_PATH)
    res = _kernel32.GetModuleFileNameW(_int2handle(module), buf, _MAX_PATH)

    if not res:
        raise _WinError()
    return _ffi.string(buf)

# #define macros from WinBase.h and elsewhere
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
DUPLICATE_SAME_ACCESS = 2
STARTF_USESTDHANDLES = 0x100
STARTF_USESHOWWINDOW = 0x001
SW_HIDE = 0
INFINITE = 0xffffffff
WAIT_OBJECT_0 = 0
WAIT_ABANDONED_0 = 0x80
WAIT_TIMEOUT = 0x102
CREATE_NEW_CONSOLE = 0x010
CREATE_NEW_PROCESS_GROUP = 0x200
CREATE_UNICODE_ENVIRONMENT = 0x400
STILL_ACTIVE = 259
_MAX_PATH = 260

ERROR_SUCCESS           = 0
ERROR_NETNAME_DELETED   = 64
ERROR_BROKEN_PIPE       = 109
ERROR_MORE_DATA         = 234
ERROR_PIPE_CONNECTED    = 535
ERROR_OPERATION_ABORTED = 995
ERROR_IO_INCOMPLETE     = 996
ERROR_IO_PENDING        = 997

PIPE_ACCESS_INBOUND = 0x00000001
PIPE_ACCESS_OUTBOUND = 0x00000002
PIPE_ACCESS_DUPLEX   = 0x00000003
PIPE_WAIT                  = 0x00000000
PIPE_NOWAIT                = 0x00000001
PIPE_READMODE_BYTE         = 0x00000000
PIPE_READMODE_MESSAGE      = 0x00000002
PIPE_TYPE_BYTE             = 0x00000000
PIPE_TYPE_MESSAGE          = 0x00000004
PIPE_ACCEPT_REMOTE_CLIENTS = 0x00000000
PIPE_REJECT_REMOTE_CLIENTS = 0x00000008

GENERIC_READ   =  0x80000000
GENERIC_WRITE  =  0x40000000
GENERIC_EXECUTE=  0x20000000
GENERIC_ALL    =  0x10000000
INVALID_HANDLE_VALUE = -1
FILE_FLAG_WRITE_THROUGH       =  0x80000000
FILE_FLAG_OVERLAPPED          =  0x40000000
FILE_FLAG_NO_BUFFERING        =  0x20000000
FILE_FLAG_RANDOM_ACCESS       =  0x10000000
FILE_FLAG_SEQUENTIAL_SCAN     =  0x08000000
FILE_FLAG_DELETE_ON_CLOSE     =  0x04000000
FILE_FLAG_BACKUP_SEMANTICS    =  0x02000000
FILE_FLAG_POSIX_SEMANTICS     =  0x01000000
FILE_FLAG_OPEN_REPARSE_POINT  =  0x00200000
FILE_FLAG_OPEN_NO_RECALL      =  0x00100000
FILE_FLAG_FIRST_PIPE_INSTANCE =  0x00080000

NMPWAIT_WAIT_FOREVER          =  0xffffffff
NMPWAIT_NOWAIT                =  0x00000001
NMPWAIT_USE_DEFAULT_WAIT      =  0x00000000

CREATE_NEW        = 1
CREATE_ALWAYS     = 2
OPEN_EXISTING     = 3
OPEN_ALWAYS       = 4
TRUNCATE_EXISTING = 5

