import os
from pypy.rpython.lltypesystem.rffi import (CConstant, CExternVariable, 
        INT, CCHARPP)
from pypy.rpython.lltypesystem import lltype, ll2ctypes, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import specialize

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
eci = ExternalCompilationInfo(
    includes=['errno.h','stdio.h'],
    separate_module_sources = separate_module_sources,
    export_symbols = export_symbols,
)

_get_errno, _set_errno = CExternVariable(INT, 'errno', eci,
                                         CConstantErrno, sandboxsafe=True,
                                         _nowrapper=True, c_type='int')
# the default wrapper for set_errno is not suitable for use in critical places
# like around GIL handling logic, so we provide our own wrappers.

def get_errno():
    return intmask(_get_errno())

def set_errno(errno):
    _set_errno(rffi.cast(INT, errno))

if os.name == 'nt':
    def validate_fd_emulator(fd):
        try:
            os.fstat(fd)
            return 1
        except:
            return 0

    validate_fd = rffi.llexternal(
        "_PyVerify_fd", [rffi.INT], rffi.INT,
        _callable=validate_fd_emulator, compilation_info=eci,
        _nowrapper=True, elidable_function=True, sandboxsafe=True,
        )
else:
    def validate_fd(fd):
        return 1
    
def closerange(fd_low, fd_high):
    # this behaves like os.closerange() from Python 2.6.
    for fd in xrange(fd_low, fd_high):
        try:
            if validate_fd(fd):
                os.close(fd)
        except OSError:
            pass

#___________________________________________________________________
# Wrappers around posix functions, that accept either strings, or
# instances with a "as_bytes()" method.
# - pypy.modules.posix.interp_posix passes an object containing a unicode path
#   which can encode itself with sys.filesystemencoding.
# - but pypy.rpython.module.ll_os.py on Windows will replace these functions
#   with other wrappers that directly handle unicode strings.
@specialize.argtype(0)
def open(path, flags, mode):
    if isinstance(path, str):
        return os.open(path, flags, mode)
    else:
        return os.open(path.as_bytes(), flags, mode)

@specialize.argtype(0)
def stat(path):
    if isinstance(path, str):
        return os.stat(path)
    else:
        return os.stat(path.as_bytes())

@specialize.argtype(0)
def lstat(path):
    if isinstance(path, str):
        return os.lstat(path)
    else:
        return os.lstat(path.as_bytes())

@specialize.argtype(0)
def unlink(path):
    if isinstance(path, str):
        return os.unlink(path)
    else:
        return os.unlink(path.as_bytes())

@specialize.argtype(0, 1)
def rename(path1, path2):
    if isinstance(path1, str):
        return os.rename(path1, path2)
    else:
        return os.rename(path1.as_bytes(), path2.as_bytes())

@specialize.argtype(0)
def listdir(dirname):
    if isinstance(dirname, str):
        return os.listdir(dirname)
    else:
        return os.listdir(dirname.as_bytes())

@specialize.argtype(0)
def access(path, mode):
    if isinstance(path, str):
        return os.access(path, mode)
    else:
        return os.access(path.as_bytes(), mode)

@specialize.argtype(0)
def chmod(path, mode):
    if isinstance(path, str):
        return os.chmod(path, mode)
    else:
        return os.chmod(path.as_bytes(), mode)

@specialize.argtype(0, 1)
def utime(path, times):
    if isinstance(path, str):
        return os.utime(path, times)
    else:
        return os.utime(path.as_bytes(), times)

@specialize.argtype(0)
def chdir(path):
    if isinstance(path, str):
        return os.chdir(path)
    else:
        return os.chdir(path.as_bytes())

@specialize.argtype(0)
def mkdir(path, mode=0777):
    if isinstance(path, str):
        return os.mkdir(path, mode)
    else:
        return os.mkdir(path.as_bytes(), mode)

@specialize.argtype(0)
def rmdir(path):
    if isinstance(path, str):
        return os.rmdir(path)
    else:
        return os.rmdir(path.as_bytes())

@specialize.argtype(0)
def mkfifo(path, mode):
    if isinstance(path, str):
        os.mkfifo(path, mode)
    else:
        os.mkfifo(path.as_bytes(), mode)

@specialize.argtype(0)
def mknod(path, mode, device):
    if isinstance(path, str):
        os.mknod(path, mode, device)
    else:
        os.mknod(path.as_bytes(), mode, device)

@specialize.argtype(0, 1)
def symlink(src, dest):
    if isinstance(src, str):
        os.symlink(src, dest)
    else:
        os.symlink(src.as_bytes(), dest.as_bytes())

if os.name == 'nt':
    import nt
    def _getfullpathname(path):
        if isinstance(path, str):
            return nt._getfullpathname(path)
        else:
            return nt._getfullpathname(path.as_bytes())
