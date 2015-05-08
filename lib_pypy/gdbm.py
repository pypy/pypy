import cffi, os, sys
import thread
_lock = thread.allocate_lock()

ffi = cffi.FFI()
ffi.cdef('''
#define GDBM_READER ...
#define GDBM_WRITER ...
#define GDBM_WRCREAT ...
#define GDBM_NEWDB ...
#define GDBM_FAST ...
#define GDBM_SYNC ...
#define GDBM_NOLOCK ...
#define GDBM_REPLACE ...

void* gdbm_open(char *, int, int, int, void (*)());
void gdbm_close(void*);

typedef struct {
    char *dptr;
    int   dsize;
} datum;

datum gdbm_fetch(void*, datum);
datum pygdbm_fetch(void*, char*, int);
int gdbm_delete(void*, datum);
int gdbm_store(void*, datum, datum, int);
int gdbm_exists(void*, datum);
int pygdbm_exists(void*, char*, int);

int gdbm_reorganize(void*);

datum gdbm_firstkey(void*);
datum gdbm_nextkey(void*, datum);
void gdbm_sync(void*);

char* gdbm_strerror(int);
int gdbm_errno;

void free(void*);
''')

try:
    verify_code = '''
    #include <stdlib.h>
    #include "gdbm.h"

    static datum pygdbm_fetch(GDBM_FILE gdbm_file, char *dptr, int dsize) {
        datum key = {dptr, dsize};
        return gdbm_fetch(gdbm_file, key);
    }

    static int pygdbm_exists(GDBM_FILE gdbm_file, char *dptr, int dsize) {
        datum key = {dptr, dsize};
        return gdbm_exists(gdbm_file, key);
    }
    
    '''
    if sys.platform.startswith('freebsd'):
        import os.path
        _localbase = os.environ.get('LOCALBASE', '/usr/local')
        lib = ffi.verify(verify_code, libraries=['gdbm'],
             include_dirs=[os.path.join(_localbase, 'include')],
             library_dirs=[os.path.join(_localbase, 'lib')]
        )
    else:
        lib = ffi.verify(verify_code, libraries=['gdbm'])
except cffi.VerificationError as e:
    # distutils does not preserve the actual message,
    # but the verification is simple enough that the
    # failure must be due to missing gdbm dev libs
    raise ImportError('%s: %s' %(e.__class__.__name__, e))

class error(Exception):
    pass

def _checkstr(key):
    if isinstance(key, unicode):
        key = key.encode("ascii")
    if not isinstance(key, str):
        raise TypeError("gdbm mappings have string indices only")
    return key

def _fromstr(key):
    if isinstance(key, unicode):
        key = key.encode("ascii")
    if not isinstance(key, str):
        raise TypeError("gdbm mappings have string indices only")
    return {'dptr': ffi.new("char[]", key), 'dsize': len(key)}

class gdbm(object):
    __ll_dbm = None

    # All public methods need to acquire the lock; all private methods
    # assume the lock is already held.  Thus public methods cannot call
    # other public methods.

    def __init__(self, filename, iflags, mode):
        with _lock:
            res = lib.gdbm_open(filename, 0, iflags, mode, ffi.NULL)
            self.__size = -1
            if not res:
                self.__raise_from_errno()
            self.__ll_dbm = res

    def close(self):
        with _lock:
            if self.__ll_dbm:
                lib.gdbm_close(self.__ll_dbm)
                self.__ll_dbm = None

    def __raise_from_errno(self):
        if ffi.errno:
            raise error(ffi.errno, os.strerror(ffi.errno))
        raise error(lib.gdbm_errno, lib.gdbm_strerror(lib.gdbm_errno))

    def __len__(self):
        with _lock:
            if self.__size < 0:
                self.__size = len(self.__keys())
            return self.__size

    def __setitem__(self, key, value):
        with _lock:
            self.__check_closed()
            self.__size = -1
            r = lib.gdbm_store(self.__ll_dbm, _fromstr(key), _fromstr(value),
                               lib.GDBM_REPLACE)
            if r < 0:
                self.__raise_from_errno()

    def __delitem__(self, key):
        with _lock:
            self.__check_closed()
            self.__size = -1
            res = lib.gdbm_delete(self.__ll_dbm, _fromstr(key))
            if res < 0:
                raise KeyError(key)

    def __contains__(self, key):
        with _lock:
            self.__check_closed()
            key = _checkstr(key)
            return lib.pygdbm_exists(self.__ll_dbm, key, len(key))
    has_key = __contains__

    def __getitem__(self, key):
        with _lock:
            self.__check_closed()
            key = _checkstr(key)
            drec = lib.pygdbm_fetch(self.__ll_dbm, key, len(key))
            if not drec.dptr:
                raise KeyError(key)
            res = str(ffi.buffer(drec.dptr, drec.dsize))
            lib.free(drec.dptr)
            return res

    def __keys(self):
        self.__check_closed()
        l = []
        key = lib.gdbm_firstkey(self.__ll_dbm)
        while key.dptr:
            l.append(str(ffi.buffer(key.dptr, key.dsize)))
            nextkey = lib.gdbm_nextkey(self.__ll_dbm, key)
            lib.free(key.dptr)
            key = nextkey
        return l

    def keys(self):
        with _lock:
            return self.__keys()

    def firstkey(self):
        with _lock:
            self.__check_closed()
            key = lib.gdbm_firstkey(self.__ll_dbm)
            if key.dptr:
                res = str(ffi.buffer(key.dptr, key.dsize))
                lib.free(key.dptr)
                return res

    def nextkey(self, key):
        with _lock:
            self.__check_closed()
            key = lib.gdbm_nextkey(self.__ll_dbm, _fromstr(key))
            if key.dptr:
                res = str(ffi.buffer(key.dptr, key.dsize))
                lib.free(key.dptr)
                return res

    def reorganize(self):
        with _lock:
            self.__check_closed()
            if lib.gdbm_reorganize(self.__ll_dbm) < 0:
                self.__raise_from_errno()

    def __check_closed(self):
        if not self.__ll_dbm:
            raise error(0, "GDBM object has already been closed")

    __del__ = close

    def sync(self):
        with _lock:
            self.__check_closed()
            lib.gdbm_sync(self.__ll_dbm)

def open(filename, flags='r', mode=0666):
    if flags[0] == 'r':
        iflags = lib.GDBM_READER
    elif flags[0] == 'w':
        iflags = lib.GDBM_WRITER
    elif flags[0] == 'c':
        iflags = lib.GDBM_WRCREAT
    elif flags[0] == 'n':
        iflags = lib.GDBM_NEWDB
    else:
        raise error(0, "First flag must be one of 'r', 'w', 'c' or 'n'")
    for flag in flags[1:]:
        if flag == 'f':
            iflags |= lib.GDBM_FAST
        elif flag == 's':
            iflags |= lib.GDBM_SYNC
        elif flag == 'u':
            iflags |= lib.GDBM_NOLOCK
        else:
            raise error(0, "Flag '%s' not supported" % flag)
    return gdbm(filename, iflags, mode)

open_flags = "rwcnfsu"
