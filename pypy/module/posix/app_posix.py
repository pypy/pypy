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


class stat_result:
    __metaclass__ = structseqtype

    st_mode  = structseqfield(0, "protection bits")
    st_ino   = structseqfield(1, "inode")
    st_dev   = structseqfield(2, "device")
    st_nlink = structseqfield(3, "number of hard links")
    st_uid   = structseqfield(4, "user ID of owner")
    st_gid   = structseqfield(5, "group ID of owner")
    st_size  = structseqfield(6, "total size, in bytes")

    # NOTE: float times are disabled for now, for compatibility with CPython.

    # access to indices 7 to 9 gives the timestamps as integers:
    #_integer_atime = structseqfield(7)
    #_integer_mtime = structseqfield(8)
    #_integer_ctime = structseqfield(9)

    st_atime = structseqfield(7, "time of last access")
    st_mtime = structseqfield(8, "time of last modification")
    st_ctime = structseqfield(9, "time of last status change")

    # further fields, not accessible by index (the numbers are still needed
    # but not visible because they are no longer consecutive)
    if "st_blksize" in posix._statfields:
        st_blksize = structseqfield(20, "blocksize for filesystem I/O")
    if "st_blocks" in posix._statfields:
        st_blocks = structseqfield(21, "number of blocks allocated")
    if "st_rdev" in posix._statfields:
        st_rdev = structseqfield(22, "device ID (if special file)")
    if "st_flags" in posix._statfields:
        st_flags = structseqfield(23, "user defined flags for file")


def fdopen(fd, mode='r', buffering=-1):
    """fdopen(fd [, mode='r' [, buffering]]) -> file_object

    Return an open file object connected to a file descriptor."""

    return file.fdopen(fd, mode, buffering)


def tmpfile():
    """Create a temporary file.

    The data in the file is freed when you
    close the file, or automatically by the OS when the program ends."""
    import tempfile
    f = tempfile.TemporaryFile()
    if osname == 'nt':
        f = f.file     # on NT, with the 2.4 stdlib of CPython,
                       # we get a _TemporaryFileWrapper for no good reason
    return f


# __________ only if we have os.fork() __________

class popenfile(file):
    _childpid = None

    def close(self):
        import os
        file.close(self)
        pid = self._childpid
        if pid is not None:
            self._childpid = None
            os.waitpid(pid, 0)
    __del__ = close     # as in CPython, __del__ may call os.waitpid()

def popen(command, mode='r', bufsize=-1):
    """popen(command [, mode='r' [, bufsize]]) -> pipe
    
    Open a pipe to/from a command returning a file object."""

    from popen2 import MAXFD
    import os, gc

    def try_close(fd):
        try:
            os.close(fd)
        except OSError:
            pass

    if not mode.startswith('r') and not mode.startswith('w'):
        raise ValueError("invalid mode %r" % (mode,))
    read_end, write_end = os.pipe()
    try:
        gc.disable_finalizers()
        try:
            childpid = os.fork()
            if childpid == 0:
                # in the child
                try:
                    if mode.startswith('r'):
                        os.dup2(write_end, 1)
                        os.close(read_end)
                    else:
                        os.dup2(read_end, 0)
                        os.close(write_end)
                    os.closerange(3, MAXFD)
                    cmd = ['/bin/sh', '-c', command]
                    os.execvp(cmd[0], cmd)
                finally:
                    os._exit(1)
        finally:
            gc.enable_finalizers()

        if mode.startswith('r'):
            os.close(write_end)
            fd = read_end
        else:
            os.close(read_end)
            fd = write_end
        g = popenfile.fdopen(fd, mode, bufsize)
        g._childpid = childpid
        return g

    except Exception, e:
        try_close(write_end)
        try_close(read_end)
        raise Exception, e     # bare 'raise' does not work here :-(
