# NOT_RPYTHON

import os
from _structseq import structseqtype, structseqfield

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
    st_atime = structseqfield(7, "time of last access (XXX as an int)")
    st_mtime = structseqfield(8, "time of last modification (XXX as an int)")
    st_ctime = structseqfield(9, "time of last change (XXX as an int)")
    # XXX no extra fields for now


def fdopen(fd, mode='r', buffering=-1):
    """fdopen(fd [, mode='r' [, buffering]]) -> file_object

    Return an open file object connected to a file descriptor."""

    return file.fdopen(fd, mode, buffering)


# __________ only if we have os.fork() __________

class popenfile(file):
    _childpid = None

    def close(self):
        file.close(self)
        pid = self._childpid
        if pid is not None:
            self._childpid = None
            os.waitpid(pid, 0)
    __del__ = close     # as in CPython, __del__ may call os.waitpid()

def try_close(fd):
    try:
        os.close(fd)
    except OSError:
        pass

def popen(command, mode='r', bufsize=-1):
    """popen(command [, mode='r' [, bufsize]]) -> pipe
    
    Open a pipe to/from a command returning a file object."""

    from popen2 import MAXFD

    if not mode.startswith('r') and not mode.startswith('w'):
        raise ValueError("invalid mode %r" % (mode,))
    read_end, write_end = os.pipe()
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
                for i in range(3, MAXFD):
                    try_close(i)
                cmd = ['/bin/sh', '-c', command]
                os.execvp(cmd[0], cmd)
            finally:
                os._exit(1)

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
