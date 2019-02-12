"""
Support routines for subprocess module.
Currently, this extension module is only required when using the
subprocess module on Windows.
"""

import sys
if sys.platform != 'win32':
    raise ImportError("The '_subprocess' module is only available on Windows")

# Declare external Win32 functions

from _pypy_winbase_cffi import ffi as _ffi
_kernel32 = _ffi.dlopen('kernel32')

GetVersion = _kernel32.GetVersion


# Now the _subprocess module implementation

def _WinError():
    code, message = _ffi.getwinerror()
    raise WindowsError(code, message)

def _int2handle(val):
    return _ffi.cast("HANDLE", val)

_INVALID_HANDLE_VALUE = _int2handle(-1)

class _handle(object):
    def __init__(self, c_handle):
        # 'c_handle' is a cffi cdata of type HANDLE, which is basically 'void *'
        self.c_handle = c_handle
        if int(self) != -1:
            self.c_handle = _ffi.gc(self.c_handle, _kernel32.CloseHandle)

    def __int__(self):
        return int(_ffi.cast("intptr_t", self.c_handle))

    def __repr__(self):
        return '<_subprocess.handle %d at 0x%x>' % (int(self), id(self))

    def Detach(self):
        h = int(self)
        if h != -1:
            c_handle = self.c_handle
            self.c_handle = _INVALID_HANDLE_VALUE
            _ffi.gc(c_handle, None)
        return h

    def Close(self):
        if int(self) != -1:
            c_handle = self.c_handle
            self.c_handle = _INVALID_HANDLE_VALUE
            _ffi.gc(c_handle, None)
            _kernel32.CloseHandle(c_handle)

def CreatePipe(attributes, size):
    handles = _ffi.new("HANDLE[2]")

    res = _kernel32.CreatePipe(handles, handles + 1, _ffi.NULL, size)

    if not res:
        raise _WinError()

    return _handle(handles[0]), _handle(handles[1])

def GetCurrentProcess():
    return _handle(_kernel32.GetCurrentProcess())

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

    return _handle(target[0])

def _z(input):
    if input is None:
        return _ffi.NULL
    if isinstance(input, basestring):
        return str(input)
    raise TypeError("string/unicode/None expected, got %r" % (
        type(input).__name__,))

def CreateProcess(name, command_line, process_attr, thread_attr,
                  inherit, flags, env, start_dir, startup_info):
    si = _ffi.new("STARTUPINFO *")
    if startup_info is not None:
        si.dwFlags = startup_info.dwFlags
        si.wShowWindow = startup_info.wShowWindow
        # CPython: these three handles are expected to be _handle objects
        if startup_info.hStdInput:
            si.hStdInput = startup_info.hStdInput.c_handle
        if startup_info.hStdOutput:
            si.hStdOutput = startup_info.hStdOutput.c_handle
        if startup_info.hStdError:
            si.hStdError = startup_info.hStdError.c_handle

    pi = _ffi.new("PROCESS_INFORMATION *")

    if env is not None:
        envbuf = ""
        for k, v in env.iteritems():
            envbuf += "%s=%s\0" % (k, v)
        envbuf += '\0'
    else:
        envbuf = _ffi.NULL

    res = _kernel32.CreateProcessA(_z(name), _z(command_line), _ffi.NULL,
                                   _ffi.NULL, inherit, flags, envbuf,
                                   _z(start_dir), si, pi)

    if not res:
        raise _WinError()

    return (_handle(pi.hProcess),
            _handle(pi.hThread),
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
        # note: returns integer, not handle object
        return int(_ffi.cast("intptr_t", res))

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
DUPLICATE_SAME_ACCESS = 2
STARTF_USESTDHANDLES = 0x100
STARTF_USESHOWWINDOW = 0x001
SW_HIDE = 0
INFINITE = 0xffffffff
WAIT_OBJECT_0 = 0
CREATE_NEW_CONSOLE = 0x010
CREATE_NEW_PROCESS_GROUP = 0x200
STILL_ACTIVE = 259
