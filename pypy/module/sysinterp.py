"""
Implementation of interpreter-level 'sys' routines.
"""
import os
from pypy.interpreter import autopath
from pypy.interpreter.module import Module
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError

import sys as cpy_sys

# Common data structures
w_modules              = space.newdict([])
w_warnoptions          = space.newlist([])
w_builtin_module_names = space.newlist([])

# Initialize the default path
srcdir = os.path.dirname(autopath.pypydir)
appdir = os.path.join(autopath.pypydir, 'appspace')
w_path = space.newlist([space.wrap(appdir)] +
                       [space.wrap(p) for p in cpy_sys.path if p!= srcdir])

# XXX - Replace with appropriate PyPy version numbering
w_hexversion = space.wrap(cpy_sys.hexversion)
w_platform   = space.wrap(cpy_sys.platform)
w_maxint     = space.wrap(cpy_sys.maxint)

w_stdin  = space.wrap(cpy_sys.stdin)
w_stdout = space.wrap(cpy_sys.stdout)
w_stderr = space.wrap(cpy_sys.stderr)


def setmodule(w_module):
    """ put a module into the modules list """
    w_name = space.getattr(w_module, space.wrap('__name__'))
    space.setitem(w_modules, w_name, w_module)

def setbuiltinmodule(w_module):
    """ put a module into modules list and builtin_module_names """
    w_name = space.getattr(w_module, space.wrap('__name__'))
    w_append = space.getattr(w_builtin_module_names, space.wrap('append'))
    space.call_function(w_append, w_name)
    space.setitem(w_modules, w_name, w_module)

def displayhook(w_x):
    w = space.wrap
    if not space.is_true(space.is_(w_x, space.w_None)):
        try:
            # XXX don't use print, send to sys.stdout instead
            print space.unwrap(space.repr(w_x))
        except OperationError:
            print "! could not print", w_x
        space.setitem(space.w_builtins, w('_'), w_x)

def _getframe():
    # XXX No Argument Accepted Yet
    f = space.getexecutioncontext().framestack.items[-1]
    return space.wrap(f)
