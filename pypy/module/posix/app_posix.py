# NOT_RPYTHON
from _structseq import structseqtype, structseqfield
from __pypy__ import validate_fd

# XXX we need a way to access the current module's globals more directly...
import errno
import sys
if 'posix' in sys.builtin_module_names:
    import posix
    osname = 'posix'
elif 'nt' in sys.builtin_module_names:
    import nt as posix
    osname = 'nt'
else:
    raise ImportError("XXX")

error = OSError


class stat_result(metaclass=structseqtype):

    name = osname + ".stat_result"

    st_mode  = structseqfield(0, "protection bits")
    st_ino   = structseqfield(1, "inode")
    st_dev   = structseqfield(2, "device")
    st_nlink = structseqfield(3, "number of hard links")
    st_uid   = structseqfield(4, "user ID of owner")
    st_gid   = structseqfield(5, "group ID of owner")
    st_size  = structseqfield(6, "total size, in bytes")

    # NOTE: float times are disabled for now, for compatibility with CPython.
    # access to indices 7 to 9 gives the timestamps as integers:
    _integer_atime = structseqfield(7)
    _integer_mtime = structseqfield(8)
    _integer_ctime = structseqfield(9)

    # further fields, not accessible by index (the numbers are still needed
    # but not visible because they are no longer consecutive)
    st_atime = structseqfield(11, "time of last access")
    st_mtime = structseqfield(12, "time of last modification")
    st_ctime = structseqfield(13, "time of last change")
    st_atime_ns = structseqfield(14, "time of last access in nanoseconds")
    st_mtime_ns = structseqfield(15, "time of last modification in nanoseconds")
    st_ctime_ns = structseqfield(16, "time of last change in nanoseconds")

    if "st_blksize" in posix._statfields:
        st_blksize = structseqfield(20, "blocksize for filesystem I/O")
    if "st_blocks" in posix._statfields:
        st_blocks = structseqfield(21, "number of blocks allocated")
    if "st_rdev" in posix._statfields:
        st_rdev = structseqfield(22, "device ID (if special file)")
    if "st_flags" in posix._statfields:
        st_flags = structseqfield(23, "user defined flags for file")

    def __init__(self, *args, **kw):
        # If we have been initialized from a tuple,
        # st_?time might be set to None. Initialize it
        # from the int slots.
        if self.st_atime is None:
            self.__dict__['st_atime'] = self[7]
        if self.st_mtime is None:
            self.__dict__['st_mtime'] = self[8]
        if self.st_ctime is None:
            self.__dict__['st_ctime'] = self[9]


class statvfs_result(metaclass=structseqtype):

    name = osname + ".statvfs_result"

    f_bsize = structseqfield(0)
    f_frsize = structseqfield(1)
    f_blocks = structseqfield(2)
    f_bfree = structseqfield(3)
    f_bavail = structseqfield(4)
    f_files = structseqfield(5)
    f_ffree = structseqfield(6)
    f_favail = structseqfield(7)
    f_flag = structseqfield(8)
    f_namemax = structseqfield(9)


class uname_result(metaclass=structseqtype):

    name = osname + ".uname_result"

    sysname  = structseqfield(0, "operating system name")
    nodename = structseqfield(1, "name of machine on network "
                              "(implementation-defined")
    release  = structseqfield(2, "operating system release")
    version  = structseqfield(3, "operating system version")
    machine  = structseqfield(4, "hardware identifier")

class terminal_size(metaclass=structseqtype):

    name = osname + ".terminal_size"

    columns  = structseqfield(0, "width of the terminal window in characters")
    lines = structseqfield(1, "height of the terminal window in characters")

if osname == 'posix':
    # POSIX: we want to check the file descriptor when fdopen() is called,
    # not later when we read or write data.  So we call fstat(), letting
    # it raise if fd is invalid.
    _validate_fd = posix.fstat
else:
    _validate_fd = validate_fd

if osname == 'posix':
    def wait():
        """ wait() -> (pid, status)

        Wait for completion of a child process.
        """
        return posix.waitpid(-1, 0)

    def wait3(options):
        """ wait3(options) -> (pid, status, rusage)

        Wait for completion of a child process and provides resource usage information
        """
        from _pypy_wait import wait3
        return wait3(options)

    def wait4(pid, options):
        """ wait4(pid, options) -> (pid, status, rusage)

        Wait for completion of the child process "pid" and provides resource usage information
        """
        from _pypy_wait import wait4
        return wait4(pid, options)

    def urandom(n):
        """urandom(n) -> str

        Return a string of n random bytes suitable for cryptographic use.

        """
        try:
            with open('/dev/urandom', 'rb', buffering=0) as fd:
                return fd.read(n)
        except OSError as e:
            if e.errno in (errno.ENOENT, errno.ENXIO, errno.ENODEV, errno.EACCES):
                raise NotImplementedError("/dev/urandom (or equivalent) not found")
            raise
