"""
Implementation of interpreter-level 'sys' routines.
"""
#from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError

import sys as cpy_sys

def hack_cpython_module(modname):
    "NOT_RPYTHON. Steal a module from CPython."
    cpy_module = __import__(modname, globals(), locals(), None)
    return cpy_module
##    # to build the dictionary of the module, we get all the objects
##    # accessible as 'self.xxx'. Methods are bound.
##    contents = []
##    for name in cpy_module.__dict__:
##        # ignore names in '_xyz'
##        if not name.startswith('_') or name.endswith('_'):
##            value = cpy_module.__dict__[name]
##            contents.append((space.wrap(name), space.wrap(value)))
##    w_contents = space.newdict(contents)
##    return Module(space, space.wrap(modname), w_contents)

# ____________________________________________________________
#
# List of built-in modules.
# It should contain the name of all the files 'module/*module.py'.
builtin_module_names = ['__builtin__', 'sys',
                        ]

# Create the builtin_modules dictionary, mapping names to Module instances
builtin_modules = {}
for fn in builtin_module_names:
    builtin_modules[fn] = None

# The following built-in modules are not written in PyPy, so we
# steal them from Python.
for fn in ['posix', 'nt', 'os2', 'mac', 'ce', 'riscos',
           'itertools', 'math', '_codecs', 'array',
           '_random', '_sre', 'time', '_socket', 'errno',
           'marshal', 'binascii', 'parser']:
    if fn not in builtin_modules:
        try:
            builtin_modules[fn] = hack_cpython_module(fn)
        except ImportError:
            pass
        else:
            builtin_module_names.append(fn)

# ____________________________________________________________
#
# Common data structures
w_modules              = space.newdict([])
w_warnoptions          = space.newlist([])
w_argv                 = space.newlist([])
builtin_module_names.sort()
w_builtin_module_names = space.newtuple([space.wrap(fn)
                                         for fn in builtin_module_names])

# Initialize the default path
import os
from pypy.interpreter import autopath
srcdir = os.path.dirname(autopath.pypydir)
appdir = os.path.join(autopath.pypydir, 'appspace')
del os, autopath # XXX for the translator. Something is very wrong around here.

w_initialpath = space.newlist([space.wrap(''), space.wrap(appdir)] +
                       [space.wrap(p) for p in cpy_sys.path if p!= srcdir])

# XXX - Replace with appropriate PyPy version numbering
w_platform   = space.wrap(cpy_sys.platform)
w_maxint     = space.wrap(cpy_sys.maxint)
w_byteorder  = space.wrap(cpy_sys.byteorder)
w_exec_prefix = space.wrap(cpy_sys.exec_prefix)
w_prefix = space.wrap(cpy_sys.prefix)
w_maxunicode = space.wrap(cpy_sys.maxunicode)
w_stdin  = space.wrap(cpy_sys.stdin)
w_stdout = space.wrap(cpy_sys.stdout)
w_stderr = space.wrap(cpy_sys.stderr)

w_pypy_objspaceclass = space.wrap(space.__class__.__name__)

# ____________________________________________________________

def setmodule(w_module):
    """ put a module into the modules dict """
    w_name = space.getattr(w_module, space.wrap('__name__'))
    space.setitem(w_modules, w_name, w_module)

def setbuiltinmodule(w_module, name):
    """ put a module into the modules builtin_modules dicts """
    if builtin_modules[name] is None:
        builtin_modules[name] = space.unwrap(w_module)
    else:
        assert builtin_modules[name] is space.unwrap(w_module), (
            "trying to change the builtin-in module %r" % (name,))
    space.setitem(w_modules, space.wrap(name), w_module)

##def displayhook(w_x):
##    w = space.wrap
##    if not space.is_true(space.is_(w_x, space.w_None)):
##        w_stdout = space.getattr(space.w_sys, space.wrap('stdout'))
##        try:
##            w_repr = space.repr(w_x)
##        except OperationError:
##            w_repr = space.wrap("! __repr__ raised an exception")
##        w_repr = space.add(w_repr, space.wrap("\n"))
##        space.call_method(w_stdout, 'write', 
##        space.setitem(space.w_builtins, w('_'), w_x)

def _getframe(w_depth=0):
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

# this variable is living here, but we
# access it this way, later:
# space.sys.recursion_limit = 1000
# note that we cannot do it *here* because
# space.sys does not exist, yet.
recursion_limit = 1000

def setrecursionlimit(w_new_limit):
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
    space.sys.recursion_limit = new_limit

def getrecursionlimit():
    """getrecursionlimit()

Return the current value of the recursion limit, the maximum depth
of the Python interpreter stack.  This limit prevents infinite
recursion from causing an overflow of the C stack and crashing Python."""

    return space.newint(recursion_limit)

checkinterval = 100

def setcheckinterval(w_interval):
    """setcheckinterval(n)

Tell the Python interpreter to check for asynchronous events every
n instructions.  This also affects how often thread switches occur."""

    space.sys.checkinterval = space.int_w(w_interval)

def getcheckinterval():
    """getcheckinterval() -> current check interval; see setcheckinterval()."""
    return space.newint(checkinterval)


def exc_info():
    operror = space.getexecutioncontext().sys_exc_info()
    if operror is None:
        return space.newtuple([space.w_None,space.w_None,space.w_None])
    else:
        return space.newtuple([operror.w_type,operror.w_value,
                               space.wrap(operror.application_traceback)])

def exc_clear():
    operror = space.getexecutioncontext().sys_exc_info()
    if operror is not None:
        operror.clear(space)

def pypy_getudir():
    """NOT_RPYTHON"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))

def getdefaultencoding():
    """getdefaultencoding() -> return the default encoding used for UNICODE"""
    return space.wrap(cpy_sys.getdefaultencoding())
