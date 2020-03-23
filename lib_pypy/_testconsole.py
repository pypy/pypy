import sys
if sys.platform != 'win32':
    raise ImportError("The '_testconsole' module is only available on Windows")
    
import _winapi

from _pypy_winbase_cffi import ffi as _ffi
_kernel32 = _ffi.dlopen('kernel32')
import _io

def write_input(file, s):
    
    # if not file is _io._WindowsConsoleIO:
    #    raise TypeError("expected raw console object")
    # Assume it is OK, for untranslated tests
    handle = getattr(file, 'handle', file)    
    size = len(s)
    
    rec = _ffi.new("INPUT_RECORD[%s]" % size)
    
    if not rec:
        return None
        
    for i in range(0,size):
        rec[i].EventType = 1  # KEY_EVENT
        rec[i].Event.KeyEvent.bKeyDown = True
        rec[i].Event.KeyEvent.wRepeatCount = 10
        rec[i].Event.KeyEvent.uChar.UnicodeChar = s[i]
    
    total = 0
    wrote = _ffi.new("DWORD[1]")
    phandle = _ffi.cast('void*', handle)
    while total < size:
        if not _kernel32.WriteConsoleInputW(phandle, rec + total, size - total, wrote):
            _winapi.SetFromWindowsErr(0)
        print('wrote', wrote[0], 'of', size-total)
        total += wrote[0]

def read_output(file):
    return None
