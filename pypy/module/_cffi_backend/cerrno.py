from pypy.rlib import rposix
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.gateway import unwrap_spec


ExecutionContext._cffi_saved_errno = 0


def get_errno_container(space):
    return space.getexecutioncontext()

get_real_errno = rposix.get_errno


def restore_errno_from(ec):
    rposix.set_errno(ec._cffi_saved_errno)

def save_errno_into(ec, errno):
    ec._cffi_saved_errno = errno


def get_errno(space):
    ec = get_errno_container(space)
    return space.wrap(ec._cffi_saved_errno)

@unwrap_spec(errno=int)
def set_errno(space, errno):
    ec = get_errno_container(space)
    ec._cffi_saved_errno = errno
