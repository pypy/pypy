import os
from rpython.rtyper.lltypesystem.rffi import CConstant, CExternVariable, INT
from rpython.rtyper.lltypesystem import ll2ctypes, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.objectmodel import specialize
from rpython.rlib import jit
from rpython.translator.platform import platform


class CConstantErrno(CConstant):
    # these accessors are used when calling get_errno() or set_errno()
    # on top of CPython
    def __getitem__(self, index):
        assert index == 0
        try:
            return ll2ctypes.TLS.errno
        except AttributeError:
            raise ValueError("no C function call occurred so far, "
                             "errno is undefined")
    def __setitem__(self, index, value):
        assert index == 0
        ll2ctypes.TLS.errno = value

if os.name == 'nt':
    if platform.name == 'msvc':
        includes=['errno.h','stdio.h']
    else:
        includes=['errno.h','stdio.h', 'stdint.h']
    separate_module_sources =['''
        /* Lifted completely from CPython 3.3 Modules/posix_module.c */
        #include <malloc.h> /* for _msize */
        typedef struct {
            intptr_t osfhnd;
            char osfile;
        } my_ioinfo;
        extern __declspec(dllimport) char * __pioinfo[];
        #define IOINFO_L2E 5
        #define IOINFO_ARRAY_ELTS   (1 << IOINFO_L2E)
        #define IOINFO_ARRAYS 64
        #define _NHANDLE_           (IOINFO_ARRAYS * IOINFO_ARRAY_ELTS)
        #define FOPEN 0x01
        #define _NO_CONSOLE_FILENO (intptr_t)-2

        /* This function emulates what the windows CRT
            does to validate file handles */
        int
        _PyVerify_fd(int fd)
        {
            const int i1 = fd >> IOINFO_L2E;
            const int i2 = fd & ((1 << IOINFO_L2E) - 1);

            static size_t sizeof_ioinfo = 0;

            /* Determine the actual size of the ioinfo structure,
             * as used by the CRT loaded in memory
             */
            if (sizeof_ioinfo == 0 && __pioinfo[0] != NULL) {
                sizeof_ioinfo = _msize(__pioinfo[0]) / IOINFO_ARRAY_ELTS;
            }
            if (sizeof_ioinfo == 0) {
                /* This should not happen... */
                goto fail;
            }

            /* See that it isn't a special CLEAR fileno */
                if (fd != _NO_CONSOLE_FILENO) {
                /* Microsoft CRT would check that 0<=fd<_nhandle but we can't do that.  Instead
                 * we check pointer validity and other info
                 */
                if (0 <= i1 && i1 < IOINFO_ARRAYS && __pioinfo[i1] != NULL) {
                    /* finally, check that the file is open */
                    my_ioinfo* info = (my_ioinfo*)(__pioinfo[i1] + i2 * sizeof_ioinfo);
                    if (info->osfile & FOPEN) {
                        return 1;
                    }
                }
            }
          fail:
            errno = EBADF;
            return 0;
        }
    ''',]
    export_symbols = ['_PyVerify_fd']
else:
    separate_module_sources = []
    export_symbols = []
    includes=['errno.h','stdio.h']
errno_eci = ExternalCompilationInfo(
    includes=includes,
    separate_module_sources=separate_module_sources,
    export_symbols=export_symbols,
)

_get_errno, _set_errno = CExternVariable(INT, 'errno', errno_eci,
                                         CConstantErrno, sandboxsafe=True,
                                         _nowrapper=True, c_type='int')
# the default wrapper for set_errno is not suitable for use in critical places
# like around GIL handling logic, so we provide our own wrappers.

def get_errno():
    return intmask(_get_errno())

def set_errno(errno):
    _set_errno(rffi.cast(INT, errno))

if os.name == 'nt':
    is_valid_fd = jit.dont_look_inside(rffi.llexternal(
        "_PyVerify_fd", [rffi.INT], rffi.INT,
        compilation_info=errno_eci,
        ))
    def validate_fd(fd):
        if not is_valid_fd(fd):
            raise OSError(get_errno(), 'Bad file descriptor')
else:
    def is_valid_fd(fd):
        return 1

    def validate_fd(fd):
        return 1

def closerange(fd_low, fd_high):
    # this behaves like os.closerange() from Python 2.6.
    for fd in xrange(fd_low, fd_high):
        try:
            if is_valid_fd(fd):
                os.close(fd)
        except OSError:
            pass

#___________________________________________________________________
# Wrappers around posix functions, that accept either strings, or
# instances with a "as_bytes()" method.
# - pypy.modules.posix.interp_posix passes an object containing a unicode path
#   which can encode itself with sys.filesystemencoding.
# - but rpython.rtyper.module.ll_os.py on Windows will replace these functions
#   with other wrappers that directly handle unicode strings.
@specialize.argtype(0)
def _as_bytes(path):
    assert path is not None
    if isinstance(path, str):
        return path
    else:
        return path.as_bytes()

@specialize.argtype(0)
def open(path, flags, mode):
    return os.open(_as_bytes(path), flags, mode)

@specialize.argtype(0)
def stat(path):
    return os.stat(_as_bytes(path))

@specialize.argtype(0)
def lstat(path):
    return os.lstat(_as_bytes(path))


@specialize.argtype(0)
def statvfs(path):
    return os.statvfs(_as_bytes(path))


@specialize.argtype(0)
def unlink(path):
    return os.unlink(_as_bytes(path))

@specialize.argtype(0, 1)
def rename(path1, path2):
    return os.rename(_as_bytes(path1), _as_bytes(path2))

@specialize.argtype(0)
def listdir(dirname):
    return os.listdir(_as_bytes(dirname))

@specialize.argtype(0)
def access(path, mode):
    return os.access(_as_bytes(path), mode)

@specialize.argtype(0)
def chmod(path, mode):
    return os.chmod(_as_bytes(path), mode)

@specialize.argtype(0, 1)
def utime(path, times):
    return os.utime(_as_bytes(path), times)

@specialize.argtype(0)
def chdir(path):
    return os.chdir(_as_bytes(path))

@specialize.argtype(0)
def mkdir(path, mode=0777):
    return os.mkdir(_as_bytes(path), mode)

@specialize.argtype(0)
def rmdir(path):
    return os.rmdir(_as_bytes(path))

@specialize.argtype(0)
def mkfifo(path, mode):
    os.mkfifo(_as_bytes(path), mode)

@specialize.argtype(0)
def mknod(path, mode, device):
    os.mknod(_as_bytes(path), mode, device)

@specialize.argtype(0, 1)
def symlink(src, dest):
    os.symlink(_as_bytes(src), _as_bytes(dest))

if os.name == 'nt':
    import nt
    @specialize.argtype(0)
    def _getfullpathname(path):
        return nt._getfullpathname(_as_bytes(path))

@specialize.argtype(0, 1)
def putenv(name, value):
    os.environ[_as_bytes(name)] = _as_bytes(value)

@specialize.argtype(0)
def unsetenv(name):
    del os.environ[_as_bytes(name)]

if os.name == 'nt':
    from rpython.rlib import rwin32
    os_kill = rwin32.os_kill
else:
    os_kill = os.kill
