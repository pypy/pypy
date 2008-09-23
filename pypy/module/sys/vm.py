"""
Implementation of interpreter-level 'sys' routines.
"""
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace
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
    try:
        f = space.getexecutioncontext().framestack.top(depth)
    except IndexError:
        raise OperationError(space.w_ValueError,
                             space.wrap("call stack is not deep enough"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("frame index must not be negative"))
    return space.wrap(f)

# directly from the C code in ceval.c, might be moved somewhere else.

def setrecursionlimit(space, w_new_limit):
    """Set the maximum depth of the Python interpreter stack to n.  This
limit prevents infinite recursion from causing an overflow of the C
stack and crashing Python.  The highest possible limit is platform
dependent."""
    new_limit = space.int_w(w_new_limit)
    if new_limit <= 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("recursion limit must be positive"))
    # global recursion_limit
    # we need to do it without writing globals.
    space.sys.recursionlimit = new_limit

def getrecursionlimit(space):
    """Return the current value of the recursion limit, the maximum depth
    of the Python interpreter stack.  This limit prevents infinite
    recursion from causing an overflow of the C stack and crashing Python.
    """

    return space.wrap(space.sys.recursionlimit)

def setcheckinterval(space, interval):
    """Tell the Python interpreter to check for asynchronous events every
    n instructions.  This also affects how often thread switches occur."""
    space.actionflag.setcheckinterval(space, interval)
setcheckinterval.unwrap_spec = [ObjSpace, int]

def getcheckinterval(space):
    """Return the current check interval; see setcheckinterval()."""
    # xxx to make tests and possibly some obscure apps happy, if the
    # checkinterval is set to the minimum possible value (which is 1) we
    # return 0.  The idea is that according to the CPython docs, <= 0
    # means "check every virtual instruction, maximizing responsiveness
    # as well as overhead".
    result = space.sys.checkinterval
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
        return space.newtuple([operror.w_type, operror.w_value,
                               space.wrap(operror.application_traceback)])

def exc_clear(space):
    """Clear global information on the current exception.  Subsequent calls
to exc_info() will return (None,None,None) until another exception is
raised and caught in the current thread or the execution stack returns to a
frame where another exception is being handled."""
    operror = space.getexecutioncontext().sys_exc_info()
    if operror is not None:
        operror.clear(space)

def pypy_getudir(space):
    """NOT_RPYTHON"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))

## def getrefcount(space, w_obj):
##     """getrefcount(object) -> integer
##     Return the reference count of object.  The count returned is generally
##     one higher than you might expect, because it includes the (temporary)
##     reference as an argument to getrefcount().
##     """
##     # From the results i get when using this i need to apply a fudge
##     # value of 6 to get results comparable to cpythons. /Arre
##     return space.wrap(sys.getrefcount(w_obj) - 6)

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
