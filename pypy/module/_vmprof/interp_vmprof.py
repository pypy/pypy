from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.baseobjspace import W_Root
from rpython.rlib import rvmprof

# ____________________________________________________________


_get_code = lambda frame, w_inputvalue, operr: frame.pycode
_decorator = rvmprof.vmprof_execute_code("pypy", _get_code, W_Root)
my_execute_frame = _decorator(PyFrame.execute_frame)


class __extend__(PyFrame):
    def execute_frame(self, w_inputvalue=None, operr=None):
        # indirection for the optional arguments
        return my_execute_frame(self, w_inputvalue, operr)


def _safe(s):
    if len(s) > 110:
        s = s[:107] + '...'
    return s.replace(':', ';')

def _get_full_name(pycode):
    # careful, must not have extraneous ':' or be longer than 255 chars
    return "py:%s:%d:%s" % (_safe(pycode.co_name), pycode.co_firstlineno,
                            _safe(pycode.co_filename))

rvmprof.register_code_object_class(PyCode, _get_full_name)


def _init_ready(pycode):
    rvmprof.register_code(pycode, _get_full_name)

PyCode._init_ready = _init_ready


# ____________________________________________________________


class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("_vmprof.error")

def vmprof_error(space, e):
    w_error = space.fromcache(Cache).w_error
    return OperationError(w_error, space.wrap(e.msg))


@unwrap_spec(fileno=int, period=float)
def enable(space, fileno, period=0.01):   # default 100 Hz
    """Enable vmprof.  Writes go to the given 'fileno', a file descriptor
    opened for writing.  *The file descriptor must remain open at least
    until disable() is called.*

    The sampling interval is optionally given by 'interval' as a number of
    seconds, as a float which must be smaller than 1.0.
    """
    try:
        rvmprof.enable(fileno, period)
    except rvmprof.VMProfError, e:
        raise vmprof_error(space, e)

def disable(space):
    """Disable vmprof.  Remember to close the file descriptor afterwards
    if necessary.
    """
    try:
        rvmprof.disable()
    except rvmprof.VMProfError, e:
        raise vmprof_error(space, e)
