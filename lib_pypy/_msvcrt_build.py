from cffi import FFI

ffi = FFI()

ffi.set_source("_msvcrt_cffi", """
#include <io.h>
#include <sys/locking.h>
#include <conio.h>
""")

ffi.cdef("""
int _open_osfhandle(intptr_t osfhandle, int flags);
intptr_t _get_osfhandle(int fd);
int _setmode(int fd, int mode);
int _locking(int fd, int mode, long nbytes);

#define LK_UNLCK ...
#define LK_LOCK ...
#define LK_NBLCK ...
#define LK_RLCK ...
#define LK_NBRLCK ...

int _kbhit(void);
char _getch(void);
wchar_t _getwch(void);
char _getche(void);
wchar_t _getwche(void);
void _putch(char);
void _putwch(wchar_t);
int _ungetch(char);

#define EOF ...
""")

if __name__ == "__main__":
    ffi.compile()
