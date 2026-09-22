from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.baseobjspace import W_Root
from rpython.rlib import rvmprof, jit
from pypy.interpreter.error import oefmt
from rpython.rlib.rarithmetic import r_uint

# ____________________________________________________________


_get_code = lambda frame, w_inputvalue, operr: frame.pycode
_decorator = rvmprof.vmprof_execute_code("pypy", _get_code, W_Root)
my_execute_frame = _decorator(PyFrame.execute_frame)

# All call sites pass exactly (w_inputvalue, operr), using None for the
# omitted ones, so this can be bound as PyFrame.execute_frame directly.
PyFrame.execute_frame = my_execute_frame


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

@unwrap_spec(addr=r_uint)
def resolve_addr(space, addr):
    """Symbolicate a native code address.  Returns a tuple
    (name, lineno, srcfile), or None if no symbol covers the address.
    """
    name, lineno, srcfile = rvmprof.resolve_addr(addr)
    if not name:
        return space.w_None
    return space.newtuple([space.newtext(name), space.newint(lineno),
                           space.newtext(srcfile)])

def resolve_many_addr(space, w_addrs):
    """Symbolicate every address in the iterable 'addrs'.  Returns a dict
    mapping the addresses that could be resolved to (name, lineno, srcfile).
    """
    w_res = space.newdict()
    for w_addr in space.unpackiterable(w_addrs):
        w_info = resolve_addr(space, space.uint_w(w_addr))
        if not space.is_w(w_info, space.w_None):
            space.setitem(w_res, w_addr, w_info)
    return w_res
