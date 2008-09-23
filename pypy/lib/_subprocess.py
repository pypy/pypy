"""
Support routines for subprocess module.
Currently, this extension module is only required when using the
subprocess module on Windows.
"""


# Declare external Win32 functions

import ctypes

_kernel32 = ctypes.WinDLL('kernel32')

_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [ctypes.c_int]
_CloseHandle.restype = ctypes.c_int

_CreatePipe = _kernel32.CreatePipe
_CreatePipe.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                        ctypes.c_void_p, ctypes.c_int]
_CreatePipe.restype = ctypes.c_int

_GetCurrentProcess = _kernel32.GetCurrentProcess
_GetCurrentProcess.argtypes = []
_GetCurrentProcess.restype = ctypes.c_int

_DuplicateHandle = _kernel32.DuplicateHandle
_DuplicateHandle.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             ctypes.POINTER(ctypes.c_int),
                             ctypes.c_int, ctypes.c_int, ctypes.c_int]
_DuplicateHandle.restype = ctypes.c_int
    
_WaitForSingleObject = _kernel32.WaitForSingleObject
_WaitForSingleObject.argtypes = [ctypes.c_int, ctypes.c_int]
_WaitForSingleObject.restype = ctypes.c_int

_GetExitCodeProcess = _kernel32.GetExitCodeProcess
_GetExitCodeProcess.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
_GetExitCodeProcess.restype = ctypes.c_int

_GetStdHandle = _kernel32.GetStdHandle
_GetStdHandle.argtypes = [ctypes.c_int]
_GetStdHandle.restype = ctypes.c_int

class _STARTUPINFO(ctypes.Structure):
    _fields_ = [('cb',         ctypes.c_int),
                ('lpReserved', ctypes.c_void_p),
                ('lpDesktop',  ctypes.c_char_p),
                ('lpTitle',    ctypes.c_char_p),
                ('dwX',        ctypes.c_int),
                ('dwY',        ctypes.c_int),
                ('dwXSize',    ctypes.c_int),
                ('dwYSize',    ctypes.c_int),
                ('dwXCountChars', ctypes.c_int),
                ('dwYCountChars', ctypes.c_int),
                ("dwFillAttribute", ctypes.c_int),
                ("dwFlags", ctypes.c_int),
                ("wShowWindow", ctypes.c_short),
                ("cbReserved2", ctypes.c_short),
                ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", ctypes.c_int),
                ("hStdOutput", ctypes.c_int),
                ("hStdError", ctypes.c_int)
                ]

class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", ctypes.c_int),
                ("hThread", ctypes.c_int),
                ("dwProcessID", ctypes.c_int),
                ("dwThreadID", ctypes.c_int)]

_CreateProcess = _kernel32.CreateProcessA
_CreateProcess.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p,
                           ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p,
                           ctypes.POINTER(_STARTUPINFO), ctypes.POINTER(_PROCESS_INFORMATION)]
_CreateProcess.restype = ctypes.c_int

del ctypes

# Now the _subprocess module implementation 

from ctypes import c_int as _c_int, byref as _byref

class _handle:
    def __init__(self, handle):
        self.handle = handle

    def __int__(self):
        return self.handle

    def Detach(self):
        handle, self.handle = self.handle, None
        return handle

    def Close(self):
        if self.handle not in (-1, None):
            _CloseHandle(self.handle)
            self.handle = None

def CreatePipe(attributes, size):
    read = _c_int()
    write = _c_int()

    res = _CreatePipe(_byref(read), _byref(write), None, size)

    if not res:
        raise WindowsError("Error")

    return _handle(read.value), _handle(write.value)

def GetCurrentProcess():
    return _handle(_GetCurrentProcess())


def DuplicateHandle(source_process, source, target_process, access, inherit, options=0):
    target = _c_int()

    res = _DuplicateHandle(int(source_process), int(source), int(target_process),
                           _byref(target),
                           access, inherit, options)

    if not res:
        raise WindowsError("Error")

    return _handle(target.value)
DUPLICATE_SAME_ACCESS = 2


def CreateProcess(name, command_line, process_attr, thread_attr,
                  inherit, flags, env, start_dir, startup_info):
    si = _STARTUPINFO()
    si.dwFlags = startup_info.dwFlags
    si.wShowWindow = getattr(startup_info, 'wShowWindow', 0)
    if startup_info.hStdInput:
        si.hStdInput = startup_info.hStdInput.handle
    if startup_info.hStdOutput:
        si.hStdOutput = startup_info.hStdOutput.handle
    if startup_info.hStdError:
        si.hStdError = startup_info.hStdError.handle

    pi = _PROCESS_INFORMATION()

    if env is not None:
        envbuf = ""
        for k, v in env.iteritems():
            envbuf += "%s=%s\0" % (k, v)
        envbuf += '\0'
    else:
        envbuf = None

    res = _CreateProcess(name, command_line, None, None, inherit, flags, envbuf,
                        start_dir, _byref(si), _byref(pi))

    if not res:
        raise WindowsError("Error")

    return _handle(pi.hProcess), _handle(pi.hThread), pi.dwProcessID, pi.dwThreadID
STARTF_USESTDHANDLES = 0x100

def WaitForSingleObject(handle, milliseconds):
    res = _WaitForSingleObject(handle.handle, milliseconds)

    if res < 0:
        raise WindowsError("Error")

    return res
INFINITE = 0xffffffff
WAIT_OBJECT_0 = 0

def GetExitCodeProcess(handle):
    code = _c_int()
    
    res = _GetExitCodeProcess(handle.handle, _byref(code))

    if not res:
        raise WindowsError("Error")

    return code.value

def GetStdHandle(stdhandle):
    res = _GetStdHandle(stdhandle)

    if not res:
        return None
    else:
        return res
STD_INPUT_HANDLE  = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE  = -12
