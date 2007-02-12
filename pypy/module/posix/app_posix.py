# NOT_RPYTHON

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

