import sys
if sys.platform != 'win32':
    raise ImportError("The '_testconsole' module is only available on Windows")
    
import _winapi

# Must work on CPython and PyPy for tests since standard CPython does not ship
# c-extension _testconsole from CPython/PC/_testconsole.c
# The cdef of INPUT_RECORD is truncated

import cffi
ffi = cffi.FFI()
ffi.cdef("""
typedef struct _KEY_EVENT_RECORD {
  BOOL  bKeyDown;
  WORD  wRepeatCount;
  WORD  wVirtualKeyCode;
  WORD  wVirtualScanCode;
  union {
    WCHAR UnicodeChar;
    CHAR  AsciiChar;
  } uChar;
  DWORD dwControlKeyState;
} KEY_EVENT_RECORD;


typedef struct _INPUT_RECORD {
  WORD  EventType;
  KEY_EVENT_RECORD KeyEvent;
} INPUT_RECORD;

int GetStdHandle(int);

int WriteConsoleInputW(HANDLE, INPUT_RECORD*, DWORD, LPDWORD);

""")

_kernel32 = ffi.dlopen('kernel32')
import _io

def write_input(file, s):
    
    # Assume it is $CONIN
    handle = _kernel32.GetStdHandle(-10)
    size = len(s)
    
    rec = ffi.new("INPUT_RECORD[%s]" % size)
    
    if not rec:
        return None
        
    for i in range(0,size):
        rec[i].EventType = 1  # KEY_EVENT
        rec[i].KeyEvent.bKeyDown = True
        rec[i].KeyEvent.wRepeatCount = 10
        rec[i].KeyEvent.uChar.UnicodeChar = s[i]
    
    total = 0
    wrote = ffi.new("DWORD[1]")
    phandle = ffi.cast('void*', handle)
    while total < size:
        if not _kernel32.WriteConsoleInputW(phandle, rec + total, size - total, wrote):
            code, message = ffi.getwinerror()
            raise WindowsError(message, code)
        print('wrote', wrote[0], 'of', size-total)
        total += wrote[0]
    print('done writing')

def read_output(file):
    return None
