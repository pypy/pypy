import os
from pypy.rpython.lltypesystem.rffi import CConstant, CExternVariable, INT
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

errno_eci = ExternalCompilationInfo(
    includes=['errno.h']
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


def closerange(fd_low, fd_high):
    # this behaves like os.closerange() from Python 2.6.
    for fd in xrange(fd_low, fd_high):
        try:
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
