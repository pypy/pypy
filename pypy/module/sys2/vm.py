"""
Implementation of interpreter-level 'sys' routines.
"""
from pypy.interpreter.error import OperationError
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
    """setrecursionlimit(n)

Set the maximum depth of the Python interpreter stack to n.  This
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
    """getrecursionlimit()
    Return the current value of the recursion limit, the maximum depth
    of the Python interpreter stack.  This limit prevents infinite
    recursion from causing an overflow of the C stack and crashing Python.
    """

    return space.wrap(space.sys.recursionlimit)

checkinterval = 100

def setcheckinterval(space, w_interval):
    """setcheckinterval(n)
    Tell the Python interpreter to check for asynchronous events every
    n instructions.  This also affects how often thread switches occur."""
    space.sys.checkinterval = space.int_w(w_interval) 

def getcheckinterval(space):
    """getcheckinterval() -> current check interval; see setcheckinterval()."""
    return space.wrap(space.sys.checkinterval)

def exc_info(space):
    operror = space.getexecutioncontext().sys_exc_info()
    if operror is None:
        return space.newtuple([space.w_None,space.w_None,space.w_None])
    else:
        return space.newtuple([operror.w_type, operror.w_value,
                               space.wrap(operror.application_traceback)])

def exc_clear(space):
    operror = space.getexecutioncontext().sys_exc_info()
    if operror is not None:
        operror.clear(space)

def pypy_getudir(space):
    """NOT_RPYTHON"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))

def getrefcount(space, w_obj):
    """getrefcount(object) -> integer
    Return the reference count of object.  The count returned is generally
    one higher than you might expect, because it includes the (temporary)
    reference as an argument to getrefcount().
    """
    # From the results i get when using this i need to apply a fudge
    # value of 6 to get results comparable to cpythons. /Arre
    return space.wrap(sys.getrefcount(w_obj) - 6)

def settrace(space, w_func):
    """settrace(function)

Set the global debug tracing function.  It will be called on each
function call.  See the debugger chapter in the library manual.
"""
    space.getexecutioncontext().settrace(w_func)
    
def setprofile(space, w_func):
    """setprofile(function)

Set the profiling function.  It will be called on each function call
and return.  See the profiler chapter in the library manual.
"""
    space.getexecutioncontext().setprofile(w_func)

