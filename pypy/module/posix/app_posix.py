# NOT_RPYTHON

from _structseq import structseqtype, structseqfield

# XXX we need a way to access the current module's globals more directly...
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

    name = "posix.stat_result"

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

    st_atime = structseqfield(15, "time of last access")
    st_mtime = structseqfield(16, "time of last modification")
    st_ctime = structseqfield(17, "time of last status change")

    if "st_blksize" in posix._statfields:
        st_blksize = structseqfield(20, "blocksize for filesystem I/O")
    if "st_blocks" in posix._statfields:
        st_blocks = structseqfield(21, "number of blocks allocated")
    if "st_rdev" in posix._statfields:
        st_rdev = structseqfield(22, "device ID (if special file)")
    if "st_flags" in posix._statfields:
        st_flags = structseqfield(23, "user defined flags for file")

    def __init__(self, *args, **kw):
        super(stat_result, self).__init__(*args, **kw)

        # If we have been initialized from a tuple,
        # st_?time might be set to None. Initialize it
        # from the int slots.
        if self.st_atime is None:
            self.__dict__['st_atime'] = self[7]
        if self.st_mtime is None:
            self.__dict__['st_mtime'] = self[8]
        if self.st_ctime is None:
            self.__dict__['st_ctime'] = self[9]

if osname == 'posix':
    def _validate_fd(fd):
        try:
            import fcntl
        except ImportError:
            return
        try:
            fcntl.fcntl(fd, fcntl.F_GETFD)
        except IOError as e:
            raise OSError(e.errno, e.strerror, e.filename)
else:
    def _validate_fd(fd):
        # XXX for the moment
        return

if osname == 'posix':
    def wait():
        """ wait() -> (pid, status)

        Wait for completion of a child process.
        """
        return posix.waitpid(-1, 0)

    def wait3(options):
        """ wait3(options) -> (pid, status, rusage)

        Wait for completion of a child process and provides resource usage informations
        """
        from _pypy_wait import wait3
        return wait3(options)

    def wait4(pid, options):
        """ wait4(pid, options) -> (pid, status, rusage)

        Wait for completion of the child process "pid" and provides resource usage informations
        """
        from _pypy_wait import wait4
        return wait4(pid, options)

else:
    # Windows implementations

    def popen2(cmd, mode="t", bufsize=-1):
        ""

        cmd = _makecmd_string(cmd)

        if mode not in ('b', 't'):
            raise ValueError("invalid mode %r" % (mode,))

        import subprocess
        p = subprocess.Popen(cmd, shell=True, bufsize=bufsize,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             universal_newlines=(mode =='t'))
        return (_wrap_close(p.stdin, p), _wrap_close(p.stdout, p))

    def popen3(cmd, mode="t", bufsize=-1):
        ""

        cmd = _makecmd_string(cmd)

        if mode not in ('b', 't'):
            raise ValueError("invalid mode %r" % (mode,))

        import subprocess
        p = subprocess.Popen(cmd, shell=True, bufsize=bufsize,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             universal_newlines=(mode =='t'))
        return (_wrap_close(p.stdin, p), _wrap_close(p.stdout, p),
                _wrap_close(p.stderr, p))

    def popen4(cmd, mode="t", bufsize=-1):
        ""

        cmd = _makecmd_string(cmd)

        if mode not in ('b', 't'):
            raise ValueError("invalid mode %r" % (mode,))

        import subprocess
        p = subprocess.Popen(cmd, shell=True, bufsize=bufsize,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=(mode =='t'))
        return (_wrap_close(p.stdin, p), _wrap_close(p.stdout, p))

    # helper for making popen cmd a string object
    def _makecmd_string(cmd):
        if isinstance(cmd, unicode):
            cmd = cmd.encode('ascii')

        if not isinstance(cmd, str):
            raise TypeError("invalid cmd type (%s, expected string)" %
                            (type(cmd),))
        return cmd

    # A proxy for a file whose close waits for the process
    class _wrap_close(object):
        def __init__(self, stream, proc):
            self._stream = stream
            self._proc = proc
        def close(self):
            self._stream.close()
            return self._proc.wait() or None    # 0 => None
        __del__ = close
        def __getattr__(self, name):
            return getattr(self._stream, name)
        def __iter__(self):
            return iter(self._stream)
