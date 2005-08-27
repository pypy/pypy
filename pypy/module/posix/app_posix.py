# NOT_RPYTHON

error = OSError


def tuple_item_getter(n):   # helper to make properties
    def getter(self):
        return self[n]
    return property(getter)


class stat_result(tuple):
    __slots__ = []

    st_mode  = tuple_item_getter(0)
    st_ino   = tuple_item_getter(1)
    st_dev   = tuple_item_getter(2)
    st_nlink = tuple_item_getter(3)
    st_uid   = tuple_item_getter(4)
    st_gid   = tuple_item_getter(5)
    st_size  = tuple_item_getter(6)
    st_atime = tuple_item_getter(7)
    st_mtime = tuple_item_getter(8)
    st_ctime = tuple_item_getter(9)

def fdopen(fd, mode='r', buffering=None):
    """fdopen(fd [, mode='r' [, buffering]]) -> file_object

    Return an open file object connected to a file descriptor."""

    try:
        return file.fdopen(fd, mode, buffering)
    except AttributeError:
        raise NotImplementedError, "fdopen only works if you use PyPy's file implementation."

