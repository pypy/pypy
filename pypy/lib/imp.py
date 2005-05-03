"""
This module provides the components needed to build your own
__import__ function.  Undocumented functions are obsolete.
"""

# XXX partial implementation

# XXX to be reviewed

import sys, os

PY_SOURCE       = 1
PY_COMPILED     = 2
C_EXTENSION     = 3
PY_RESOURCE     = 4
PKG_DIRECTORY   = 5
C_BUILTIN       = 6
PY_FROZEN       = 7
PY_CODERESOURCE = 8

def get_magic():
    return '\x3b\xf2\x0d\x0a'

def get_suffixes():
    return [('.py', 'U', PY_SOURCE)]

new_module = type(sys)


def find_module(name, path=None):
    if path is None:
        if name in sys.builtin_module_names:
            return (None, name, ('', '', C_BUILTIN))
        path = sys.path
    for base in path:
        filename = os.path.join(base, name)
        if os.path.isdir(filename):
            return (None, filename, ('', '', PKG_DIRECTORY))
        filename += '.py'
        if os.path.exists(filename):
            return (file(filename, 'U'), filename, ('.py', 'U', PY_SOURCE))
    raise ImportError, 'No module named %s' % (name,)


def load_module(name, file, filename, description):
    suffix, mode, type = description
    module = sys.modules.get(name)

    if type == PY_SOURCE:
        source = file.read()
        co = compile(source, filename, 'exec')
        if module is None:
            sys.modules[name] = module = new_module(name)
        module.__name__ = name
        module.__doc__ = None
        module.__file__ = filename
        exec co in module.__dict__
        return module

    if type == PKG_DIRECTORY:
        initfilename = os.path.join(filename, '__init__.py')
        if module is None:
            sys.modules[name] = module = new_module(name)
        module.__name__ = name
        module.__doc__ = None
        module.__file__ = initfilename
        module.__path__ = [filename]
        execfile(initfilename, module.__dict__)
        return module

    if type == C_BUILTIN:
        module = __import__(name, {}, {}, None)
        return module

    raise ValueError, 'invalid description argument: %r' % (description,)


# XXX needs to be implemented when we have threads
def lock_held():
    return False
def acquire_lock():
    pass
def release_lock():
    pass
