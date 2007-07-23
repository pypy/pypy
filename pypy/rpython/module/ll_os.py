"""
Low-level implementations for the external functions of the 'os' module.
"""

# Implementation details about those functions
# might be found in doc/rffi.txt

import os, errno
from pypy.rpython.module.support import ll_strcpy, _ll_strfill, OOSupport
from pypy.rpython.module.support import to_opaque_object, from_opaque_object
from pypy.rlib import ros
from pypy.rlib.rarithmetic import r_longlong
from pypy.tool.staticmethods import ClassMethods
import stat
from pypy.rpython.extfunc import ExtFuncEntry, register_external
from pypy.annotation.model import SomeString, SomeInteger, s_ImpossibleValue, \
    s_None
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype

# ------------------------------- os.execv ------------------------------

if hasattr(os, 'execv'):

    os_execv = rffi.llexternal('execv', [rffi.CCHARP, rffi.CCHARPP],
                               rffi.INT)

    def execv_lltypeimpl(path, args):
        l_path = rffi.str2charp(path)
        l_args = rffi.liststr2charpp(args)
        os_execv(l_path, l_args)
        rffi.free_charpp(l_args)
        rffi.free_charp(l_path)
        raise OSError(rffi.c_errno, "execv failed")

    register_external(os.execv, [str, [str]], s_ImpossibleValue, llimpl=
                      execv_lltypeimpl, export_name="ll_os.ll_os_execv")

# ------------------------------- os.dup --------------------------------

os_dup = rffi.llexternal('dup', [rffi.INT], rffi.INT)

def dup_lltypeimpl(fd):
    newfd = rffi.cast(lltype.Signed, os_dup(rffi.cast(rffi.INT, fd)))
    if newfd == -1:
        raise OSError(rffi.c_errno, "dup failed")
    return newfd
register_external(os.dup, [int], int, llimpl=dup_lltypeimpl,
                  export_name="ll_os.ll_os_dup", oofakeimpl=os.dup)

# ------------------------------- os.dup2 -------------------------------

os_dup2 = rffi.llexternal('dup2', [rffi.INT, rffi.INT], rffi.INT)

def dup2_lltypeimpl(fd, newfd):
    error = rffi.cast(lltype.Signed, os_dup2(rffi.cast(rffi.INT, fd),
                                             rffi.cast(rffi.INT, newfd)))
    if error == -1:
        raise OSError(rffi.c_errno, "dup2 failed")
register_external(os.dup2, [int, int], s_None, llimpl=dup2_lltypeimpl,
                  export_name="ll_os.ll_os_dup2")

# ------------------------------- os.utime ------------------------------

TIME_T = rffi.INT    # XXX do the right thing
UTIMEBUFP = rffi.CStruct('utimbuf', ('actime', TIME_T),
                                    ('modtime', TIME_T))

# XXX sys/types.h is not portable at all
ros_utime = rffi.llexternal('utime', [rffi.CCHARP, UTIMEBUFP], rffi.INT,
                            includes=['utime.h', 'sys/types.h'])

def utime_null_lltypeimpl(path):
    l_path = rffi.str2charp(path)
    error = rffi.cast(lltype.Signed, ros_utime(l_path,
                                               lltype.nullptr(UTIMEBUFP.TO)))
    rffi.free_charp(l_path)
    if error == -1:
        raise OSError(rffi.c_errno, "utime_null failed")
register_external(ros.utime_null, [str], s_None, "ll_os.utime_null",
                  llimpl=utime_null_lltypeimpl)

def utime_tuple_lltypeimpl(path, tp):
    # XXX right now they're all ints, might change in future
    # XXX does not use utimes, even when available
    l_path = rffi.str2charp(path)
    l_utimebuf = lltype.malloc(UTIMEBUFP.TO, flavor='raw')
    actime, modtime = tp
    l_utimebuf.c_actime, l_utimebuf.c_modtime = int(actime), int(modtime)
    error = rffi.cast(lltype.Signed, ros_utime(l_path, l_utimebuf))
    rffi.free_charp(l_path)
    lltype.free(l_utimebuf, flavor='raw')
    if error == -1:
        raise OSError(rffi.c_errno, "utime_tuple failed")
register_external(ros.utime_tuple, [str, (float, float)], s_None, "ll_os.utime_tuple",
                  llimpl=utime_tuple_lltypeimpl)

# ------------------------------- os.setsid -----------------------------

if hasattr(os, 'setsid'):
    os_setsid = rffi.llexternal('setsid', [], rffi.PID_T,
                                includes=['unistd.h'])

    def setsid_lltypeimpl():
        result = rffi.cast(lltype.Signed, os_setsid())
        if result == -1:
            raise OSError(rffi.c_errno, "os_setsid failed")
        return result

    register_external(os.setsid, [], int, export_name="ll_os.ll_os_setsid",
                      llimpl=setsid_lltypeimpl)

# ------------------------------- os.uname ------------------------------

if hasattr(os, 'uname'):
    UTSNAMEP = rffi.CStruct('utsname', ('sysname', rffi.CCHARP),
                            ('nodename', rffi.CCHARP),
                            ('release', rffi.CCHARP),
                            ('version', rffi.CCHARP),
                            ('machine', rffi.CCHARP),
                            ('stuff', rffi.CCHARP))
    
    os_uname = rffi.llexternal('uname', [UTSNAMEP], rffi.INT,
                               includes=['sys/utsname.h'])

    def uname_lltypeimpl():
        l_utsbuf = lltype.malloc(UTSNAMEP.TO, flavor='raw')
        result = os_uname(l_utsbuf)
        if result == -1:
            raise OSError(rffi.c_errno, "os_uname failed")
        fields = [l_utsbuf.c_sysname, l_utsbuf.c_nodename,
                l_utsbuf.c_release, l_utsbuf.c_version, l_utsbuf.c_machine]
        l = [rffi.charp2str(i) for i in fields]
        retval = (l[0], l[1], l[2], l[3], l[4])
        lltype.free(l_utsbuf, flavor='raw')
        return retval

    register_external(os.uname, [], (str, str, str, str, str),
                      "ll_os.ll_uname", llimpl=uname_lltypeimpl)

# ------------------------------- os.open -------------------------------

if os.name == 'nt':
    mode_t = rffi.INT
else:
    mode_t = rffi.MODE_T

os_open = rffi.llexternal('open', [rffi.CCHARP, rffi.INT, mode_t],
                          rffi.INT)

def os_open_lltypeimpl(path, flags, mode):
    l_path = rffi.str2charp(path)
    result = rffi.cast(lltype.Signed, os_open(l_path,
                                              rffi.cast(rffi.INT, flags),
                                              rffi.cast(mode_t, mode)))
    rffi.free_charp(l_path)
    if result == -1:
        raise OSError(rffi.c_errno, "os_open failed")
    return result

def os_open_oofakeimpl(o_path, flags, mode):
    return os.open(o_path._str, flags, mode)

register_external(os.open, [str, int, int], int, "ll_os.ll_os_open",
                  llimpl=os_open_lltypeimpl, oofakeimpl=os_open_oofakeimpl)

# ------------------------------- os.read -------------------------------

os_read = rffi.llexternal('read', [rffi.INT, rffi.VOIDP, rffi.SIZE_T],
                          rffi.SIZE_T)

def os_read_lltypeimpl(fd, count):
    if count < 0:
        raise OSError(errno.EINVAL, None)
    inbuf = lltype.malloc(rffi.CCHARP.TO, count, flavor='raw')
    try:
        got = rffi.cast(lltype.Signed, os_read(rffi.cast(rffi.INT, fd),
                                               inbuf,
                                               rffi.cast(rffi.SIZE_T, count)))
        if got < 0:
            raise OSError(rffi.c_errno, "os_read failed")
        # XXX too many copies of the data!
        l = [inbuf[i] for i in range(got)]
    finally:
        lltype.free(inbuf, flavor='raw')
    return ''.join(l)

def os_read_oofakeimpl(fd, count):
    return OOSupport.to_rstr(os.read(fd, count))

register_external(os.read, [int, int], str, "ll_os.ll_os_read",
                  llimpl=os_read_lltypeimpl, oofakeimpl=os_read_oofakeimpl)

# '--sandbox' support
def os_read_marshal_input(msg, fd, buf, size):
    msg.packnum(rffi.cast(lltype.Signed, fd))
    msg.packsize_t(size)
def os_read_unmarshal_output(msg, fd, buf, size):
    data = msg.nextstring()
    if len(data) > rffi.cast(lltype.Signed, size):
        raise OverflowError
    for i in range(len(data)):
        buf[i] = data[i]
    return rffi.cast(rffi.SIZE_T, len(data))
os_read._obj._marshal_input = os_read_marshal_input
os_read._obj._unmarshal_output = os_read_unmarshal_output

# ------------------------------- os.write ------------------------------

os_write = rffi.llexternal('write', [rffi.INT, rffi.VOIDP, rffi.SIZE_T],
                           rffi.SIZE_T)

def os_write_lltypeimpl(fd, data):
    count = len(data)
    outbuf = lltype.malloc(rffi.CCHARP.TO, count, flavor='raw')
    try:
        for i in range(count):
            outbuf[i] = data[i]
        written = rffi.cast(lltype.Signed, os_write(rffi.cast(rffi.INT, fd),
                                                    outbuf,
                                                rffi.cast(rffi.SIZE_T, count)))
        if written < 0:
            raise OSError(rffi.c_errno, "os_write failed")
    finally:
        lltype.free(outbuf, flavor='raw')
    return written

def os_write_oofakeimpl(fd, data):
    return os.write(fd, OOSupport.from_rstr(data))

register_external(os.write, [int, str], SomeInteger(nonneg=True)
                  , "ll_os.ll_os_write",
                  llimpl=os_write_lltypeimpl, oofakeimpl=os_write_oofakeimpl)

# '--sandbox' support
def os_write_marshal_input(msg, fd, buf, size):
    msg.packnum(rffi.cast(lltype.Signed, fd))
    msg.packbuf(buf, 0, rffi.cast(lltype.Signed, size))
os_write._obj._marshal_input = os_write_marshal_input

# ------------------------------- os.close ------------------------------

os_close = rffi.llexternal('close', [rffi.INT], rffi.INT)

def close_lltypeimpl(fd):
    error = rffi.cast(lltype.Signed, os_close(rffi.cast(rffi.INT, fd)))
    if error == -1:
        raise OSError(rffi.c_errno, "close failed")

register_external(os.close, [int], s_None, llimpl=close_lltypeimpl,
                  export_name="ll_os.ll_os_close", oofakeimpl=os.close)

# ------------------------------- os.* ----------------------------------

w_star = ['WCOREDUMP', 'WIFCONTINUED', 'WIFSTOPPED',
          'WIFSIGNALED', 'WIFEXITED', 'WEXITSTATUS',
          'WSTOPSIG', 'WTERMSIG']
# last 3 are returning int
w_star_returning_int = dict.fromkeys(w_star[-3:])

def declare_new_w_star(name):
    """ stupid workaround for the python late-binding
    'feature'
    """
    def fake(status):
        return int(getattr(os, name)(status))
    fake.func_name = 'fake_' + name

    
    os_c_func = rffi.llexternal(name, [lltype.Signed],
                                lltype.Signed, _callable=fake,
                                includes=["sys/wait.h", "sys/types.h"])
    
    if name in w_star_returning_int:
        def lltypeimpl(status):
            return os_c_func(status)
        resulttype = int
    else:
        def lltypeimpl(status):
            return bool(os_c_func(status))
        resulttype = bool
    lltypeimpl.func_name = name + '_lltypeimpl'
    register_external(getattr(os, name), [int], resulttype, "ll_os."+name,
                      llimpl=lltypeimpl)


for name in w_star:
    if hasattr(os, name):
        declare_new_w_star(name)

# ------------------------------- os.ttyname ----------------------------

if hasattr(os, 'ttyname'):
    os_ttyname = rffi.llexternal('ttyname', [lltype.Signed], rffi.CCHARP)

    def ttyname_lltypeimpl(fd):
        l_name = os_ttyname(fd)
        if not l_name:
            raise OSError(rffi.c_errno, "ttyname raised")
        return rffi.charp2str(l_name)

    register_external(os.ttyname, [int], str, "ll_os.ttyname",
                      llimpl=ttyname_lltypeimpl)

class BaseOS:
    __metaclass__ = ClassMethods

    def ll_os_getcwd(cls):
        return cls.to_rstr(os.getcwd())
    ll_os_getcwd.suggested_primitive = True

    def ll_os_access(cls, path, mode):
        return os.access(cls.from_rstr(path), mode)
    ll_os_access.suggested_primitive = True

    def ll_os_lseek(cls, fd,pos,how):
        return r_longlong(os.lseek(fd,pos,how))
    ll_os_lseek.suggested_primitive = True

    def ll_os_isatty(cls, fd):
        return os.isatty(fd)
    ll_os_isatty.suggested_primitive = True

    def ll_os_ftruncate(cls, fd,len):
        return os.ftruncate(fd,len)
    ll_os_ftruncate.suggested_primitive = True

    def ll_os_fstat(cls, fd):
        (stat0, stat1, stat2, stat3, stat4,
         stat5, stat6, stat7, stat8, stat9) = os.fstat(fd)
        return cls.ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                                  stat5, stat6, stat7, stat8, stat9)
    ll_os_fstat.suggested_primitive = True

    def ll_os_stat(cls, path):
        (stat0, stat1, stat2, stat3, stat4,
         stat5, stat6, stat7, stat8, stat9) = os.stat(cls.from_rstr(path))
        return cls.ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                                  stat5, stat6, stat7, stat8, stat9)
    ll_os_stat.suggested_primitive = True

    def ll_os_lstat(cls, path):
        (stat0, stat1, stat2, stat3, stat4,
         stat5, stat6, stat7, stat8, stat9) = os.lstat(cls.from_rstr(path))
        return cls.ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                                  stat5, stat6, stat7, stat8, stat9)
    ll_os_lstat.suggested_primitive = True

    def ll_os_strerror(cls, errnum):
        return cls.to_rstr(os.strerror(errnum))
    ll_os_strerror.suggested_primitive = True

    def ll_os_system(cls, cmd):
        return os.system(cls.from_rstr(cmd))
    ll_os_system.suggested_primitive = True

    def ll_os_unlink(cls, path):
        os.unlink(cls.from_rstr(path))
    ll_os_unlink.suggested_primitive = True

    def ll_os_chdir(cls, path):
        os.chdir(cls.from_rstr(path))
    ll_os_chdir.suggested_primitive = True

    def ll_os_mkdir(cls, path, mode):
        os.mkdir(cls.from_rstr(path), mode)
    ll_os_mkdir.suggested_primitive = True

    def ll_os_rmdir(cls, path):
        os.rmdir(cls.from_rstr(path))
    ll_os_rmdir.suggested_primitive = True

    # this function is not really the os thing, but the internal one.
    def ll_os_putenv(cls, name_eq_value):
        ros.putenv(cls.from_rstr(name_eq_value))
    ll_os_putenv.suggested_primitive = True

    def ll_os_unsetenv(cls, name):
        os.unsetenv(cls.from_rstr(name))
    ll_os_unsetenv.suggested_primitive = True

    # get the initial environment by indexing
    def ll_os_environ(cls, idx):
        return ros.environ(idx)
    ll_os_environ.suggested_primitive = True

    def ll_os_pipe(cls):
        fd1, fd2 = os.pipe()
        return cls.ll_pipe_result(fd1, fd2)
    ll_os_pipe.suggested_primitive = True

    def ll_os_chmod(cls, path, mode):
        os.chmod(cls.from_rstr(path), mode)
    ll_os_chmod.suggested_primitive = True

    def ll_os_rename(cls, path1, path2):
        os.rename(cls.from_rstr(path1), cls.from_rstr(path2))
    ll_os_rename.suggested_primitive = True

    def ll_os_umask(cls, mask):
        return os.umask(mask)
    ll_os_umask.suggested_primitive = True

    def ll_os_getpid(cls):
        return os.getpid()
    ll_os_getpid.suggested_primitive = True

    def ll_os_kill(cls, pid, sig):
        os.kill(pid, sig)
    ll_os_kill.suggested_primitive = True

    def ll_os_link(cls, path1, path2):
        os.link(cls.from_rstr(path1), cls.from_rstr(path2))
    ll_os_link.suggested_primitive = True

    def ll_os_symlink(cls, path1, path2):
        os.symlink(cls.from_rstr(path1), cls.from_rstr(path2))
    ll_os_symlink.suggested_primitive = True

    def ll_readlink_into(cls, path, buffer):
        data = os.readlink(cls.from_rstr(path))
        if len(data) < len(buffer.chars):   # safely no overflow
            _ll_strfill(buffer, data, len(data))
        return len(data)
    ll_readlink_into.suggested_primitive = True
    ll_readlink_into = staticmethod(ll_readlink_into)

    def ll_os_fork(cls):
        return os.fork()
    ll_os_fork.suggested_primitive = True

    def ll_os_spawnv(cls, mode, path, args):
        return os.spawnv(mode, path, args)
    ll_os_spawnv.suggested_primitive = True

    def ll_os_waitpid(cls, pid, options):
        pid, status = os.waitpid(pid, options)
        return cls.ll_waitpid_result(pid, status)
    ll_os_waitpid.suggested_primitive = True

    def ll_os__exit(cls, status):
        os._exit(status)
    ll_os__exit.suggested_primitive = True

    # ____________________________________________________________
    # opendir/readdir

    def ll_os_opendir(cls, dirname):
        dir = ros.opendir(cls.from_rstr(dirname))
        return to_opaque_object(dir)
    ll_os_opendir.suggested_primitive = True

    def ll_os_readdir(cls, opaquedir):
        dir = from_opaque_object(opaquedir)
        nextentry = dir.readdir()
        return cls.to_rstr(nextentry)
    ll_os_readdir.suggested_primitive = True

    def ll_os_closedir(cls, opaquedir):
        dir = from_opaque_object(opaquedir)
        dir.closedir()
    ll_os_closedir.suggested_primitive = True
