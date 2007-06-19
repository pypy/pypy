"""
Low-level implementations for the external functions of the 'os' module.
"""

# actual idea might be found in doc/rffi.txt

# ------------------------------------------
# WARNING! old vision, don't use it WARNING!
# ------------------------------------------

# Idea: each ll_os_xxx() function calls back the os.xxx() function that it
# is supposed to implement, either directly or indirectly if there is some
# argument decoding and buffering preparation that can be done here.

# The specific function that calls back to os.xxx() is tagged with the
# 'suggested_primitive' flag.  The back-end should special-case it and really
# implement it.  The back-end can actually choose to special-case any function:
# it can for example special-case ll_os_xxx() directly even if the
# 'suggested_primitive' flag is set to another function, if the conversion
# and buffer preparation stuff is not useful.

import sys
import os
from pypy.rpython.module.support import ll_strcpy, _ll_strfill
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

if hasattr(os, 'execv'):

    if os.name == 'nt':
        name = '_execv'
    else:
        name = 'execv'
    os_execv = rffi.llexternal(name, [rffi.CCHARP, rffi.CCHARPP],
                               lltype.Signed)

    def execv_lltypeimpl(path, args):
        l_path = rffi.str2charp(path)
        l_args = rffi.liststr2charpp(args)
        os_execv(l_path, l_args)
        rffi.free_charpp(l_args)
        lltype.free(l_path, flavor='raw')
        raise OSError(rffi.c_errno, "execv failed")

    register_external(os.execv, [str, [str]], s_ImpossibleValue, llimpl=
                      execv_lltypeimpl, export_name="ll_os.ll_os_execv")

if os.name == 'nt':
    name = '_dup'
else:
    name = 'dup'

os_dup = rffi.llexternal(name, [lltype.Signed], lltype.Signed,
                         _callable=os.dup)

def dup_lltypeimpl(fd):
    newfd = os_dup(fd)
    if newfd == -1:
        raise OSError(rffi.c_errno, "dup failed")
    return newfd
register_external(os.dup, [int], int, llimpl=dup_lltypeimpl,
                  export_name="ll_os.ll_os_dup", oofakeimpl=os.dup)

if os.name == 'nt':
    name = '_dup2'
else:
    name = 'dup2'
os_dup2 = rffi.llexternal(name, [lltype.Signed, lltype.Signed], lltype.Signed)

def dup2_lltypeimpl(fd, newfd):
    error = os_dup2(fd, newfd)
    if error == -1:
        raise OSError(rffi.c_errno, "dup2 failed")
register_external(os.dup2, [int, int], s_None, llimpl=dup2_lltypeimpl,
                  export_name="ll_os.ll_os_dup2")


UTIMEBUFP = rffi.CStruct('utimbuf', ('actime', rffi.SIZE_T),
                         ('modtime', rffi.SIZE_T))

# XXX sys/types.h is not portable at all
ros_utime = rffi.llexternal('utime', [rffi.CCHARP, UTIMEBUFP], lltype.Signed,
                            includes=['utime.h', 'sys/types.h'])

def utime_null_lltypeimpl(path):
    l_path = rffi.str2charp(path)
    error = ros_utime(l_path, lltype.nullptr(UTIMEBUFP.TO))
    lltype.free(l_path, flavor='raw')
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
    error = ros_utime(l_path, l_utimebuf)
    lltype.free(l_path, flavor='raw')
    lltype.free(l_utimebuf, flavor='raw')
    if error == -1:
        raise OSError(rffi.c_errno, "utime_tuple failed")
register_external(ros.utime_tuple, [str, (float, float)], s_None, "ll_os.utime_tuple",
                  llimpl=utime_tuple_lltypeimpl)    

def fake_os_open(l_path, flags, mode):
    path = rffi.charp2str(l_path)
    return os.open(path, flags, mode)

if sys.platform == 'nt':
    mode_t = lltype.Signed
else:
    mode_t = rffi.MODE_T

os_open = rffi.llexternal('open', [rffi.CCHARP, lltype.Signed, mode_t],
                          lltype.Signed, _callable=fake_os_open)

def os_open_lltypeimpl(path, flags, mode):
    l_path = rffi.str2charp(path)
    mode = lltype.cast_primitive(mode_t, mode)
    result = os_open(l_path, flags, mode)
    lltype.free(l_path, flavor='raw')
    if result == -1:
        raise OSError(rffi.c_errno, "os_open failed")
    return result

def os_open_oofakeimpl(o_path, flags, mode):
    return os.open(o_path._str, flags, mode)

register_external(os.open, [str, int, int], int, "ll_os.ll_os_open",
                  llimpl=os_open_lltypeimpl, oofakeimpl=os_open_oofakeimpl)

if hasattr(os, 'WIFSIGNALED'):
    def fake_WIFSIGNALED(status):
        return int(os.WIFSIGNALED(status))

    os_WIFSIGNALED = rffi.llexternal('WIFSIGNALED', [lltype.Signed],
                                     lltype.Signed,
                                     _callable=fake_WIFSIGNALED)

    def WIFSIGNALED_lltypeimpl(status):
        return bool(os_WIFSIGNALED(status))

    register_external(os.WIFSIGNALED, [int], bool, "ll_os.WIFSIGNALED",
                      llimpl=WIFSIGNALED_lltypeimpl)

class BaseOS:
    __metaclass__ = ClassMethods

    def ll_os_write(cls, fd, astring):
        return os.write(fd, cls.from_rstr(astring))
    ll_os_write.suggested_primitive = True

    def ll_os_getcwd(cls):
        return cls.to_rstr(os.getcwd())
    ll_os_getcwd.suggested_primitive = True

    def ll_read_into(fd, buffer):
        data = os.read(fd, len(buffer.chars))
        _ll_strfill(buffer, data, len(data))
        return len(data)
    ll_read_into.suggested_primitive = True
    ll_read_into = staticmethod(ll_read_into)

    def ll_os_close(cls, fd):
        os.close(fd)
    ll_os_close.suggested_primitive = True

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

    #def ll_os_execv(cls, cmd, args):
    #    os.execv(cmd, args)
    #ll_os_execv.suggested_primitive = True

    #def ll_os_execve(cls, cmd, args, env):
    #    env_list = from_rdict(env)
    #    ll_execve(cmd, args, env_list)

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
