from pypy.rlib import rposix
from pypy.interpreter.gateway import unwrap_spec


class ErrnoContainer(object):
    # XXXXXXXXXXXXXX! thread-safety
    errno = 0

errno_container = ErrnoContainer()


def restore_errno():
    rposix.set_errno(errno_container.errno)

def save_errno():
    errno_container.errno = rposix.get_errno()


def get_errno(space):
    return space.wrap(errno_container.errno)

@unwrap_spec(errno=int)
def set_errno(space, errno):
    errno_container.errno = errno
