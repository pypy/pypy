"""
Not An os or Nano os :-)

Implementation of a few methods needed for starting up
PyPy in app_main without importing os there.

At startup time, app_main wants to find out about itself,
sys.executable, the path to its library etc.
This is done the easiest using os.py, but since this
is a python module, we have a recurrence problem.

Importing it at compile time would work, partially,
but the way os is initialized will cause os.getenv
to malfunction, due to caching problems.

The solution taken here implements a minimal os using
app-level code that is created at compile-time. Only
the few needed functions are implemented in a tiny os module
that contains a tiny path module.

os.getenv got a direct implementation to overcome the caching
problem.

Please adjust the applevel code below, if you need to support
more from os and os.path.
"""

from pypy.interpreter.gateway import applevel, ObjSpace, W_Root, interp2app
import os

app_os_path = applevel(r'''
    from os.path import dirname, join, abspath, isfile, islink
''', filename=__file__)

app_os = applevel(r'''
    from os import sep, pathsep, getenv, name, fdopen
    try:
        from os import readlink
    except ImportError:
        pass
''', filename=__file__)

def getenv(space, w_name):
    name = space.str_w(w_name)
    return space.wrap(os.environ.get(name))
getenv_w = interp2app(getenv, unwrap_spec=[ObjSpace, W_Root])

def setup_nanos(space):
    w_os = space.wrap(app_os.buildmodule(space, 'os'))
    w_os_path = space.wrap(app_os_path.buildmodule(space, 'path'))
    space.setattr(w_os, space.wrap('path'), w_os_path)
    space.setattr(w_os, space.wrap('getenv'), space.wrap(getenv_w))
    return w_os


# in order to be able to test app_main without the pypy interpreter
# we create the nanos module with the same names here like it would
# be created while translation
path_module_for_testing = type(os)("os.path")
os_module_for_testing = type(os)("os")
os_module_for_testing.path = path_module_for_testing
eval(app_os_path.code, path_module_for_testing.__dict__)
eval(app_os.code, os_module_for_testing.__dict__)

