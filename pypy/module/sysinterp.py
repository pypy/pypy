"""
Implementation of interpreter-level 'sys' routines.
"""
import os
from pypy.interpreter import autopath
from pypy.interpreter.module import Module
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError

import sys as cpy_sys

def hack_cpython_module(modname):
    "Steal a module from CPython."
    cpy_module = __import__(modname, globals(), locals(), None)
    # to build the dictionary of the module, we get all the objects
    # accessible as 'self.xxx'. Methods are bound.
    contents = []
    for name in cpy_module.__dict__:
        # ignore names in '_xyz'
        if not name.startswith('_') or name.endswith('_'):
            value = cpy_module.__dict__[name]
            contents.append((space.wrap(name), space.wrap(value)))
    w_contents = space.newdict(contents)
    return Module(space, space.wrap(modname), w_contents)


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
           'cStringIO', 'itertools', 'math',
           '_random', '_sre', 'time']:
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
builtin_module_names.sort()
w_builtin_module_names = space.newtuple([space.wrap(fn)
                                         for fn in builtin_module_names])

# Initialize the default path
srcdir = os.path.dirname(autopath.pypydir)
appdir = os.path.join(autopath.pypydir, 'appspace')
w_path = space.newlist([space.wrap(''), space.wrap(appdir)] +
                       [space.wrap(p) for p in cpy_sys.path if p!= srcdir])

# XXX - Replace with appropriate PyPy version numbering
w_hexversion = space.wrap(cpy_sys.hexversion)
w_platform   = space.wrap(cpy_sys.platform)
w_maxint     = space.wrap(cpy_sys.maxint)

w_stdin  = space.wrap(cpy_sys.stdin)
w_stdout = space.wrap(cpy_sys.stdout)
w_stderr = space.wrap(cpy_sys.stderr)

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
