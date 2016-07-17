# Note: uses the CFFI out-of-line ABI mode.  We can't use the API
# mode because ffi.compile() needs to run the compiler, which
# needs 'subprocess', which needs 'msvcrt' already.

from cffi import FFI

ffi = FFI()

ffi.set_source("_msvcrt_cffi", None)

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

if __name__ == "__main__":
    ffi.compile()
