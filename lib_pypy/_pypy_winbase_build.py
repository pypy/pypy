# Note: uses the CFFI out-of-line ABI mode.  We can't use the API
# mode because ffi.compile() needs to run the compiler, which
# needs 'subprocess', which needs 'msvcrt' and '_subprocess',
# which depend on '_pypy_winbase_cffi' already.
#
# Note that if you need to regenerate _pypy_winbase_cffi and
# can't use a preexisting PyPy to do that, then running this
# file should work as long as 'subprocess' is not imported
# by cffi.  I had to hack in 'cffi._pycparser' to move an
#'import subprocess' to the inside of a function.  (Also,
# CPython+CFFI should work as well.)
#
# This module supports both msvcrt.py and _subprocess.py.

from cffi import FFI

ffi = FFI()

ffi.set_source("_pypy_winbase_cffi", None)

# ---------- MSVCRT ----------

ffi.cdef("""
typedef unsigned short wint_t;

int _open_osfhandle(intptr_t osfhandle, int flags);
intptr_t _get_osfhandle(int fd);
int _setmode(int fd, int mode);
int _locking(int fd, int mode, long nbytes);

int _kbhit(void);
int _getch(void);
wint_t _getwch(void);
int _getche(void);
wint_t _getwche(void);
int _putch(int);
wint_t _putwch(wchar_t);
int _ungetch(int);
wint_t _ungetwch(wint_t);
""")

# ---------- SUBPROCESS ----------

ffi.cdef("""
typedef struct {
    DWORD  cb;
    char * lpReserved;
    char * lpDesktop;
    char * lpTitle;
    DWORD  dwX;
    DWORD  dwY;
    DWORD  dwXSize;
    DWORD  dwYSize;
    DWORD  dwXCountChars;
    DWORD  dwYCountChars;
    DWORD  dwFillAttribute;
    DWORD  dwFlags;
    WORD   wShowWindow;
    WORD   cbReserved2;
    LPBYTE lpReserved2;
    HANDLE hStdInput;
    HANDLE hStdOutput;
    HANDLE hStdError;
} STARTUPINFO, *LPSTARTUPINFO;

typedef struct {
    HANDLE hProcess;
    HANDLE hThread;
    DWORD  dwProcessId;
    DWORD  dwThreadId;
} PROCESS_INFORMATION, *LPPROCESS_INFORMATION;

DWORD WINAPI GetVersion(void);
BOOL WINAPI CreatePipe(PHANDLE, PHANDLE, void *, DWORD);
BOOL WINAPI CloseHandle(HANDLE);
HANDLE WINAPI GetCurrentProcess(void);
BOOL WINAPI DuplicateHandle(HANDLE, HANDLE, HANDLE, LPHANDLE,
                            DWORD, BOOL, DWORD);
BOOL WINAPI CreateProcessA(char *, char *, void *,
                           void *, BOOL, DWORD, char *,
                           char *, LPSTARTUPINFO, LPPROCESS_INFORMATION);
BOOL WINAPI CreateProcessW(wchar_t *, wchar_t *, void *,
                           void *, BOOL, DWORD, wchar_t *,
                           wchar_t *, LPSTARTUPINFO, LPPROCESS_INFORMATION);
DWORD WINAPI WaitForSingleObject(HANDLE, DWORD);
BOOL WINAPI GetExitCodeProcess(HANDLE, LPDWORD);
BOOL WINAPI TerminateProcess(HANDLE, UINT);
HANDLE WINAPI GetStdHandle(DWORD);
DWORD WINAPI GetModuleFileNameW(HANDLE, wchar_t *, DWORD);

UINT WINAPI SetErrorMode(UINT);
#define SEM_FAILCRITICALERRORS     0x0001
#define SEM_NOGPFAULTERRORBOX      0x0002
#define SEM_NOALIGNMENTFAULTEXCEPT 0x0004
#define SEM_NOOPENFILEERRORBOX     0x8000
""")

# --------------------

if __name__ == "__main__":
    ffi.compile()
