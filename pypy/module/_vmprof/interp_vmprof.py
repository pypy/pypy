from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from rpython.rlib import rvmprof
from pypy.interpreter.error import oefmt

# the execute_frame wrapper and the PyCode registration are set up in
# pypy/interpreter/pyframe.py, so that they exist without this module

# ____________________________________________________________


class Cache:
    def __init__(self, space):
        self.w_VMProfError = space.new_exception_class("_vmprof.VMProfError")

def VMProfError(space, e):
    w_VMProfError = space.fromcache(Cache).w_VMProfError
    return OperationError(w_VMProfError, space.newtext(e.msg))


@unwrap_spec(fileno=int, period=float, memory=int, lines=int, native=int, real_time=int)
def enable(space, fileno, period, memory, lines, native, real_time):
    """Enable vmprof.  Writes go to the given 'fileno', a file descriptor
    opened for writing.  *The file descriptor must remain open at least
    until disable() is called.*

    'interval' is a float representing the sampling interval, in seconds.
    Must be smaller than 1.0
    """
    try:
        rvmprof.enable(fileno, period, memory, native, real_time)
    except rvmprof.VMProfError as e:
        raise VMProfError(space, e)

def disable(space):
    """Disable vmprof.  Remember to close the file descriptor afterwards
    if necessary.
    """
    try:
        rvmprof.disable()
    except rvmprof.VMProfError as e:
        raise VMProfError(space, e)

def is_enabled(space):
    return space.newbool(rvmprof.is_enabled())

def get_profile_path(space):
    path = rvmprof.get_profile_path(space)
    if path is None:
        # profiling is not enabled
        return space.w_None
    if path == "":
        # Indicates an error! Assume platform does not implement the function call
        raise oefmt(space.w_NotImplementedError, "platform not implemented")
    return space.newtext(path)

def stop_sampling(space):
    return space.newint(rvmprof.stop_sampling())

def start_sampling(space):
    rvmprof.start_sampling()
    return space.w_None
