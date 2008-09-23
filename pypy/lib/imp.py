"""
This module provides the components needed to build your own
__import__ function.
"""

# XXX partial implementation

# XXX to be reviewed

PY_SOURCE       = 1
PY_COMPILED     = 2
C_EXTENSION     = 3
PY_RESOURCE     = 4
PKG_DIRECTORY   = 5
C_BUILTIN       = 6
PY_FROZEN       = 7
PY_CODERESOURCE = 8

import new
import sys, os

# PyPy-specific interface
try:
    from sys import _magic as _get_magic_as_int
    def get_magic():
        """Return the magic number for .pyc or .pyo files."""
        import struct
        return struct.pack('<i', _get_magic_as_int())
except ImportError:
    # XXX CPython testing hack: delegate to the real imp.get_magic
    get_magic = __import__('imp').get_magic

def get_suffixes():
    """Return a list of (suffix, mode, type) tuples describing the files
    that find_module() looks for."""
    return [('.py', 'U', PY_SOURCE),
            ('.pyc', 'rb', PY_COMPILED)]


def find_module(name, path=None):
    """find_module(name, [path]) -> (file, filename, (suffix, mode, type))
    Search for a module.  If path is omitted or None, search for a
    built-in, frozen or special module and continue search in sys.path.
    The module name cannot contain '.'; to search for a submodule of a
    package, pass the submodule name and the package's __path__.
    """
    if path is None:
        if name in sys.builtin_module_names:
            return (None, name, ('', '', C_BUILTIN))
        path = sys.path
    for base in path:
        filename = os.path.join(base, name)
        if os.path.isdir(filename):
            return (None, filename, ('', '', PKG_DIRECTORY))
        for ext, mode, kind in get_suffixes():
            if os.path.exists(filename+ext):
                return (file(filename+ext, mode), filename+ext, (ext, mode, kind))
    raise ImportError, 'No module named %s' % (name,)


def load_module(name, file, filename, description):
    """Load a module, given information returned by find_module().
    The module name must include the full package name, if any.
    """
    suffix, mode, type = description

    if type == PY_SOURCE:
        return load_source(name, filename, file)

    if type == PKG_DIRECTORY:
        initfilename = os.path.join(filename, '__init__.py')
        module = sys.modules.setdefault(name, new_module(name))
        module.__name__ = name
        module.__doc__ = None
        module.__file__ = initfilename
        module.__path__ = [filename]
        execfile(initfilename, module.__dict__)
        return module

    if type == C_BUILTIN:
        module = __import__(name, {}, {}, None)
        return module
    if type == PY_COMPILED:
       return  load_compiled(name, filename, file)
    raise ValueError, 'invalid description argument: %r' % (description,)

def load_dynamic(name, *args, **kwds):
    raise ImportError(name)

def load_source(name, pathname, file=None):
    autoopen = file is None
    if autoopen:
        file = open(pathname, 'U')
    source = file.read()
    if autoopen:
        file.close()
    co = compile(source, pathname, 'exec')
    return run_module(name, pathname, co)

def load_compiled(name, pathname, file=None):
    import marshal
    autoopen = file is None
    if autoopen:
        file = open(pathname, 'rb')
    magic = file.read(4)
    if magic != get_magic():
        raise ImportError("Bad magic number in %s" % pathname)
    file.read(4)    # skip timestamp
    co = marshal.load(file)
    if autoopen:
        file.close()
    return run_module(name, pathname, co)

def run_module(name, pathname, co):
    module = sys.modules.setdefault(name, new_module(name))
    module.__name__ = name
    module.__doc__ = None
    module.__file__ = pathname
    try:
        exec co in module.__dict__
    except :
        sys.modules.pop(name,None)
        raise
    return module
 

def new_module(name):
    """Create a new module.  Do not enter it in sys.modules.
    The module name must include the full package name, if any.
    """
    return new.module(name)


def init_builtin(name):
    if name not in sys.builtin_module_names:
        return None
    if name in sys.modules:
        raise ImportError("cannot initialize a built-in module twice "
                          "in PyPy")
    return __import__(name)

def init_frozen(name):
    return None

def is_builtin(name):
    if name in sys.builtin_module_names:
        return -1   # cannot be initialized again
    else:
        return 0

def is_frozen(name):
    return False

# ____________________________________________________________

try:
    # PyPy-specific interface
    from thread import _importlock_held    as lock_held
    from thread import _importlock_acquire as acquire_lock
    from thread import _importlock_release as release_lock
except ImportError:
    def lock_held():
        """On platforms without threads, return False."""
        return False
    def acquire_lock():
        """On platforms without threads, this function does nothing."""
    def release_lock():
        """On platforms without threads, this function does nothing."""
