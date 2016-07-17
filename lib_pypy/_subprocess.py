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

class _handle:
    def __init__(self, handle):
        self.handle = handle

    def __int__(self):
        return self.handle

    def __del__(self):
        if self.handle is not None:
            _kernel32.CloseHandle(self.handle)

    def Detach(self):
        handle, self.handle = self.handle, None
        return handle

    def Close(self):
        if self.handle not in (-1, None):
            _kernel32.CloseHandle(self.handle)
            self.handle = None

def CreatePipe(attributes, size):
    handles = _ffi.new("HANDLE[2]")

    res = _kernel32.CreatePipe(handles, handles + 1, _ffi.NULL, size)

    if not res:
        raise _WinError()

    return _handle(handles[0]), _handle(handles[1])

def GetCurrentProcess():
    return _handle(_kernel32.GetCurrentProcess())

def DuplicateHandle(source_process, source, target_process, access, inherit, options=0):
    target = _ffi.new("HANDLE[1]")

    res = _kernel32.DuplicateHandle(
        int(source_process), int(source), int(target_process),
        target, access, inherit, options)

    if not res:
        raise _WinError()

    return _handle(target[0])

def CreateProcess(name, command_line, process_attr, thread_attr,
                  inherit, flags, env, start_dir, startup_info):
    si = _ffi.new("STARTUPINFO *")
    if startup_info is not None:
        si.dwFlags = startup_info.dwFlags
        si.wShowWindow = startup_info.wShowWindow
        if startup_info.hStdInput:
            si.hStdInput = int(startup_info.hStdInput)
        if startup_info.hStdOutput:
            si.hStdOutput = int(startup_info.hStdOutput)
        if startup_info.hStdError:
            si.hStdError = int(startup_info.hStdError)

    pi = _ffi.new("PROCESS_INFORMATION *")

    if env is not None:
        envbuf = ""
        for k, v in env.iteritems():
            envbuf += "%s=%s\0" % (k, v)
        envbuf += '\0'
    else:
        envbuf = _ffi.NULL

    if name is None: name = _ffi.NULL
    if command_line is None: command_line = _ffi.NULL
    if start_dir is None: start_dir = _ffi.NULL

    res = _kernel32.CreateProcessA(name, command_line, _ffi.NULL,
                                   _ffi.NULL, inherit, flags, envbuf,
                                   start_dir, si, pi)

    if not res:
        raise _WinError()

    return _handle(pi.hProcess), _handle(pi.hThread), pi.dwProcessID, pi.dwThreadID

def WaitForSingleObject(handle, milliseconds):
    res = _kernel32.WaitForSingleObject(int(handle), milliseconds)

    if res < 0:
        raise _WinError()

    return res

def GetExitCodeProcess(handle):
    code = _ffi.new("DWORD[1]")

    res = _kernel32.GetExitCodeProcess(int(handle), code)

    if not res:
        raise _WinError()

    return code[0]

def TerminateProcess(handle, exitcode):
    exitcode = _ffi.cast("UINT", exitcode)
    res = _kernel32.TerminateProcess(int(handle), exitcode)

    if not res:
        raise _WinError()

def GetStdHandle(stdhandle):
    res = _kernel32.GetStdHandle(stdhandle)

    if not res:
        return None
    else:
        return res

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
