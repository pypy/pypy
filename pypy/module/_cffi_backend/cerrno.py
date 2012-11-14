import sys
from pypy.rlib import rposix
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.gateway import unwrap_spec

WIN32 = sys.platform == 'win32'
if WIN32:
    from pypy.rlib import rwin32


ExecutionContext._cffi_saved_errno = 0
ExecutionContext._cffi_saved_LastError = 0


def get_errno_container(space):
    return space.getexecutioncontext()

get_real_errno = rposix.get_errno


def restore_errno_from(ec):
    if WIN32:
        rwin32.SetLastError(ec._cffi_saved_LastError)
    rposix.set_errno(ec._cffi_saved_errno)

def save_errno_into(ec, errno):
    ec._cffi_saved_errno = errno
    if WIN32:
        ec._cffi_saved_LastError = rwin32.GetLastError()


def get_errno(space):
    ec = get_errno_container(space)
    return space.wrap(ec._cffi_saved_errno)

@unwrap_spec(errno=int)
def set_errno(space, errno):
    ec = get_errno_container(space)
    ec._cffi_saved_errno = errno
