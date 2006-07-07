"""
Dummy low-level implementations for the external functions of the 'os' module.
"""

# Idea: each ll_os_xxx() function calls back the os.xxx() function that it
# is supposed to implement, either directly or indirectly if there is some
# argument decoding and buffering preparation that can be done here.

# The specific function that calls back to os.xxx() is tagged with the
# 'suggested_primitive' flag.  The back-end should special-case it and really
# implement it.  The back-end can actually choose to special-case any function:
# it can for example special-case ll_os_xxx() directly even if the
# 'suggested_primitive' flag is set to another function, if the conversion
# and buffer preparation stuff is not useful.

import os, errno
from pypy.rpython.module.support import ll_strcpy, _ll_strfill
from pypy.rpython.module.support import to_opaque_object, from_opaque_object
from pypy.rpython import ros
from pypy.rpython.rarithmetic import r_longlong
from pypy.tool.staticmethods import ClassMethods
import stat

class BaseOS:
    __metaclass__ = ClassMethods

    def ll_os_open(cls, fname, flag, mode):
        return os.open(cls.from_rstr(fname), flag, mode)
    ll_os_open.suggested_primitive = True

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

    def ll_os_dup(cls, fd):
        return os.dup(fd)
    ll_os_dup.suggested_primitive = True

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
