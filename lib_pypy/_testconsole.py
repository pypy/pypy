import sys
if sys.platform != 'win32':
    raise ImportError("The '_testconsole' module is only available on Windows")
    
import _winapi

from _pypy_winbase_cffi import ffi as _ffi
_kernel32 = _ffi.dlopen('kernel32')

def write_input(module, file, s):
    
    if not file is _WindowsConsoleIO:
        raise TypeError("expected raw console object")
        
    p = _ffi.new("wchar_t[]", s)
    size = len(s) / _ffi.sizeof("wchar_t")
    
    rec = _ffi.new("INPUT_RECORD", size)
    
    if not rec:
        return None
        
    for i in range(0,size):
        rec[i].EventType = KEY_EVENT
        rec[i].Event.KeyEvent.bKeyDown = true
        rec[i].Event.KeyEvent.wRepeatCount = 10
        rec[i].Event.KeyEvent.uChar.UnicodeChar = p[i]
    
    handle = file.handle
    total = _ffi.new("DWORD", 0)
    wrote = _ffi.new("DWORD", 0)
    while total < size:
        if not _kernel32.WriteConsoleInputW(handle, rec[total[0]], size - total[0], wrote):
            _winapi.SetFromWindowsErr(0)
        total[0] += wrote[0]

def read_output(module, file):
    return None
