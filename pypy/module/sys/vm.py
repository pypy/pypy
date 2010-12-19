"""
Implementation of interpreter-level 'sys' routines.
"""
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace
from pypy.rlib.runicode import MAXUNICODE
import sys

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
    return space.wrap(f)

def setrecursionlimit(space, w_new_limit):
    """setrecursionlimit() is ignored (and not needed) on PyPy.

On CPython it would set the maximum number of nested calls that can
occur before a RuntimeError is raised.  On PyPy overflowing the stack
also causes RuntimeErrors, but the limit is checked at a lower level.
(The limit is currenty hard-coded at 768 KB, corresponding to roughly
1480 Python calls on Linux.)"""
    new_limit = space.int_w(w_new_limit)
    if new_limit <= 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("recursion limit must be positive"))
    # for now, don't rewrite a warning but silently ignore the
    # recursion limit.
    #space.warn('setrecursionlimit() is ignored (and not needed) on PyPy', space.w_RuntimeWarning)
    space.sys.recursionlimit = new_limit

def getrecursionlimit(space):
    """Return the last value set by setrecursionlimit().
    """
    return space.wrap(space.sys.recursionlimit)

def setcheckinterval(space, interval):
    """Tell the Python interpreter to check for asynchronous events every
    n instructions.  This also affects how often thread switches occur."""
    space.actionflag.setcheckinterval(interval)
setcheckinterval.unwrap_spec = [ObjSpace, int]

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
                               space.wrap(operror.application_traceback)])

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

def call_tracing(space, w_func, w_args):
    """Call func(*args), while tracing is enabled.  The tracing state is
saved, and restored afterwards.  This is intended to be called from
a debugger from a checkpoint, to recursively debug some other code."""
    return space.getexecutioncontext().call_tracing(w_func, w_args)

def getwindowsversion(space):
    from pypy.rlib import rwin32
    info = rwin32.GetVersionEx()
    return space.newtuple([space.wrap(info[0]),
                           space.wrap(info[1]),
                           space.wrap(info[2]),
                           space.wrap(info[3]),
                           space.wrap(info[4])])
