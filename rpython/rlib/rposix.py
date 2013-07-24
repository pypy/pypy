import os
from rpython.rtyper.lltypesystem.rffi import CConstant, CExternVariable, INT
from rpython.rtyper.lltypesystem import ll2ctypes, lltype, rffi
from rpython.rtyper.tool import rffi_platform
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
    includes=['errno.h', 'stdio.h', 'stdlib.h', 'unistd.h',
              'sys/stat.h', 'sys/statvfs.h',
              'fcntl.h', 'signal.h', 'pty.h', 'sys/utsname.h', 'sys/wait.h',
              'sysexits.h', 'limits.h']
rposix_eci = ExternalCompilationInfo(
    includes=includes,
    separate_module_sources=separate_module_sources,
    export_symbols=export_symbols,
)

class CConfig:
    _compilation_info_ = rposix_eci

    HAVE_DEVICE_MACROS = rffi_platform.Has("makedev(major(0),minor(0))")

for name in '''
        ttyname chmod fchmod chown lchown fchown chroot link symlink readlink
        ftruncate getloadavg nice uname execv execve fork spawnv spawnve
        putenv unsetenv fchdir fsync fdatasync mknod
        fstatvfs statvfs
        openpty forkpty mkfifo getlogin sysconf fpathconf
        getsid getuid geteuid getgid getegid getpgrp getpgid
        setsid setuid seteuid setgid setegid setpgrp setpgid
        getppid getgroups setreuid setregid
        wait wait3 wait4 killpg waitpid
        '''.split():
    symbol = 'HAVE_' + name.upper()
    setattr(CConfig, symbol, rffi_platform.Has(name))

for name in '''
        F_OK R_OK W_OK X_OK NGROUPS_MAX TMP_MAX
        WNOHANG WCONTINUED WUNTRACED
        O_RDONLY O_WRONLY O_RDWR O_NDELAY O_NONBLOCK O_APPEND
        O_DSYNC O_RSYNC O_SYNC O_NOCTTY O_CREAT O_EXCL O_TRUNC
        O_BINARY O_TEXT O_LARGEFILE O_SHLOCK O_EXLOCK
        O_NOINHERIT O_TEMPORARY O_RANDOM O_SEQUENTIAL
        O_ASYNC O_DIRECT O_DIRECTORY O_NOFOLLOW O_NOATIME 
        EX_OK EX_USAGE EX_DATAERR EX_NOINPUT EX_NOUSER EX_NOHOST
        EX_UNAVAILABLE EX_SOFTWARE EX_OSERR EX_OSFILE EX_CANTCREAT
        EX_IOERR EX_TEMPFAIL EX_PROTOCOL EX_NOPERM EX_CONFIG EX_NOTFOUND
        '''.split():
    setattr(CConfig, name, rffi_platform.DefinedConstantInteger(name))

wait_macros_returning_int = ['WEXITSTATUS', 'WSTOPSIG', 'WTERMSIG']
wait_macros_returning_bool = ['WCOREDUMP', 'WIFCONTINUED', 'WIFSTOPPED',
                              'WIFSIGNALED', 'WIFEXITED']
wait_macros = wait_macros_returning_int + wait_macros_returning_bool
for name in wait_macros:
    setattr(CConfig, 'HAVE_' + name, rffi_platform.Defined(name))

globals().update(rffi_platform.configure(CConfig))


_get_errno, _set_errno = CExternVariable(INT, 'errno', rposix_eci,
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
        compilation_info=rposix_eci,
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

# Expose posix functions
def external(name, args, result, **kwargs):
    return rffi.llexternal(
        name, args, result,
        compilation_info=CConfig._compilation_info_, **kwargs)

c_fchmod = external('fchmod', [rffi.INT, rffi.MODE_T], rffi.INT)
c_fchown = external('fchown', [rffi.INT, rffi.INT, rffi.INT], rffi.INT)

for name in wait_macros:
    globals()[name] = external(name, [lltype.Signed], lltype.Signed,
                               macro=True)


#___________________________________________________________________
# Wrappers around posix functions, that accept either strings, or
# instances with a "as_bytes()" method.
# - pypy.modules.posix.interp_posix passes an object containing a unicode path
#   which can encode itself with sys.filesystemencoding.
# - but rpython.rtyper.module.ll_os.py on Windows will replace these functions
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
def statvfs(path):
    if isinstance(path, str):
        return os.statvfs(path)
    else:
        return os.statvfs(path.as_bytes())


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

@specialize.argtype(0, 1)
def putenv(name, value):
    if isinstance(name, str):
        os.environ[name] = value
    else:
        os.environ[name.as_bytes()] = value.as_bytes()

@specialize.argtype(0)
def unsetenv(name):
    if isinstance(name, str):
        del os.environ[name]
    else:
        del os.environ[name.as_bytes()]

if os.name == 'nt':
    from rpython.rlib import rwin32
    os_kill = rwin32.os_kill
else:
    os_kill = os.kill
