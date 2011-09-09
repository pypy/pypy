"""
Implementation of interpreter-level 'sys' routines.
"""
import sys

from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec, NoneNotWrapped
from pypy.rlib import jit
from pypy.rlib.runicode import MAXUNICODE

# ____________________________________________________________

def setbuiltinmodule(w_module, name):
    """ put a module into the modules builtin_modules dicts """
    if builtin_modules[name] is None:
        builtin_modules[name] = space.unwrap(w_module)
    else:
        assert builtin_modules[name] is space.unwrap(w_module), (
            "trying to change the builtin-in module %r" % (name,))
    space.setitem(w_modules, space.wrap(name), w_module)

def _getframe(space, w_depth=0):
    """Return a frame object from the call stack.  If optional integer depth is
given, return the frame object that many calls below the top of the stack.
If that is deeper than the call stack, ValueError is raised.  The default
for depth is zero, returning the frame at the top of the call stack.

This function should be used for internal and specialized
purposes only."""
    depth = space.int_w(w_depth)
    if depth < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("frame index must not be negative"))
    ec = space.getexecutioncontext()
    f = ec.gettopframe_nohidden()
    while True:
        if f is None:
            raise OperationError(space.w_ValueError,
                                 space.wrap("call stack is not deep enough"))
        if depth == 0:
            break
        depth -= 1
        f = ec.getnextframe_nohidden(f)
    f.mark_as_escaped()
    return space.wrap(f)

def _current_frames(space):
    """_current_frames() -> dictionary

    Return a dictionary mapping each current thread T's thread id to T's
    current stack frame.

    This function should be used for specialized purposes only."""
    w_result = space.newdict()
    ecs = space.threadlocals.getallvalues()
    for thread_ident, ec in ecs.items():
        f = ec.gettopframe_nohidden()
        f.mark_as_escaped()
        space.setitem(w_result,
                      space.wrap(thread_ident),
                      space.wrap(f))
    return w_result

def setrecursionlimit(space, w_new_limit):
    """setrecursionlimit() sets the maximum number of nested calls that
can occur before a RuntimeError is raised.  On PyPy the limit is
approximative and checked at a lower level.  The default 1000
reserves 768KB of stack space, which should suffice (on Linux,
depending on the compiler settings) for ~1400 calls.  Setting the
value to N reserves N/1000 times 768KB of stack space.
"""
    from pypy.rlib.rstack import _stack_set_length_fraction
    new_limit = space.int_w(w_new_limit)
    if new_limit <= 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("recursion limit must be positive"))
    space.sys.recursionlimit = new_limit
    if space.config.translation.type_system == 'lltype':
        _stack_set_length_fraction(new_limit * 0.001)

def getrecursionlimit(space):
    """Return the last value set by setrecursionlimit().
    """
    return space.wrap(space.sys.recursionlimit)

@unwrap_spec(interval=int)
def setcheckinterval(space, interval):
    """Tell the Python interpreter to check for asynchronous events every
    n instructions.  This also affects how often thread switches occur."""
    space.actionflag.setcheckinterval(interval)

def getcheckinterval(space):
    """Return the current check interval; see setcheckinterval()."""
    # xxx to make tests and possibly some obscure apps happy, if the
    # checkinterval is set to the minimum possible value (which is 1) we
    # return 0.  The idea is that according to the CPython docs, <= 0
    # means "check every virtual instruction, maximizing responsiveness
    # as well as overhead".
    result = space.actionflag.getcheckinterval()
    if result <= 1:
        result = 0
    return space.wrap(result)

def exc_info(space):
    """Return the (type, value, traceback) of the most recent exception
caught by an except clause in the current stack frame or in an older stack
frame."""
    operror = space.getexecutioncontext().sys_exc_info()
    if operror is None:
        return space.newtuple([space.w_None,space.w_None,space.w_None])
    else:
        return space.newtuple([operror.w_type, operror.get_w_value(space),
                               space.wrap(operror.get_traceback())])

def exc_clear(space):
    """Clear global information on the current exception.  Subsequent calls
to exc_info() will return (None,None,None) until another exception is
raised and caught in the current thread or the execution stack returns to a
frame where another exception is being handled."""
    operror = space.getexecutioncontext().sys_exc_info()
    if operror is not None:
        operror.clear(space)

def settrace(space, w_func):
    """Set the global debug tracing function.  It will be called on each
function call.  See the debugger chapter in the library manual."""
    space.getexecutioncontext().settrace(w_func)

def setprofile(space, w_func):
    """Set the profiling function.  It will be called on each function call
and return.  See the profiler chapter in the library manual."""
    space.getexecutioncontext().setprofile(w_func)

def getprofile(space):
    """Set the profiling function.  It will be called on each function call
and return.  See the profiler chapter in the library manual."""
    w_func = space.getexecutioncontext().getprofile()
    if w_func is not None:
        return w_func
    else:
        return space.w_None

def call_tracing(space, w_func, w_args):
    """Call func(*args), while tracing is enabled.  The tracing state is
saved, and restored afterwards.  This is intended to be called from
a debugger from a checkpoint, to recursively debug some other code."""
    return space.getexecutioncontext().call_tracing(w_func, w_args)


app = gateway.applevel('''
"NOT_RPYTHON"
from _structseq import structseqtype, structseqfield

class windows_version_info:
    __metaclass__ = structseqtype

    name = "sys.getwindowsversion"

    major = structseqfield(0, "Major version number")
    minor = structseqfield(1, "Minor version number")
    build = structseqfield(2, "Build number")
    platform = structseqfield(3, "Operating system platform")
    service_pack = structseqfield(4, "Latest Service Pack installed on the system")
''')

def getwindowsversion(space):
    from pypy.rlib import rwin32
    info = rwin32.GetVersionEx()
    w_windows_version_info = app.wget(space, "windows_version_info")
    raw_version = space.newtuple([
        space.wrap(info[0]),
        space.wrap(info[1]),
        space.wrap(info[2]),
        space.wrap(info[3]),
        space.wrap(info[4])
    ])
    return space.call_function(w_windows_version_info, raw_version)

@jit.dont_look_inside
def get_dllhandle(space):
    if not space.config.objspace.usemodules.cpyext:
        return space.wrap(0)
    if not space.config.objspace.usemodules._rawffi:
        return space.wrap(0)

    return _get_dllhandle(space)

def _get_dllhandle(space):
    # Retrieve cpyext api handle
    from pypy.module.cpyext.api import State
    handle = space.fromcache(State).get_pythonapi_handle()

    # Make a dll object with it
    from pypy.module._rawffi.interp_rawffi import W_CDLL, RawCDLL
    cdll = RawCDLL(handle)
    return space.wrap(W_CDLL(space, "python api", cdll))

def getsizeof(space, w_object, w_default=NoneNotWrapped):
    """Not implemented on PyPy."""
    if w_default is None:
        raise OperationError(space.w_TypeError,
            space.wrap("sys.getsizeof() not implemented on PyPy"))
    return w_default
