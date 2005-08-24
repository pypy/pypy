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

def get_magic():
    """Return the magic number for .pyc or .pyo files."""
    return 'm\xf2\r\n'     # XXX hard-coded: the magic of Python 2.4.1

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
    import sys, os
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
    """Load a module, given information returned by find_module().
    The module name must include the full package name, if any.
    """
    import sys, os
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

    raise ValueError, 'invalid description argument: %r' % (description,)

def load_source(name, pathname, file=None):
    import sys
    autoopen = file is None
    if autoopen:
        file = open(pathname, 'U')
    source = file.read()
    if autoopen:
        file.close()
    co = compile(source, pathname, 'exec')
    module = sys.modules.setdefault(name, new_module(name))
    module.__name__ = name
    module.__doc__ = None
    module.__file__ = pathname
    exec co in module.__dict__
    return module

def load_compiled(name, pathname, file=None):
    import sys, marshal
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
    module = sys.modules.setdefault(name, new_module(name))
    module.__name__ = name
    module.__doc__ = None
    module.__file__ = pathname
    exec co in module.__dict__
    return module


def new_module(name):
    """Create a new module.  Do not enter it in sys.modules.
    The module name must include the full package name, if any.
    """
    import new
    return new.module(name)


def init_builtin(name):
    import sys
    if name not in sys.builtin_module_names:
        return None
    if name in sys.modules:
        raise ImportError("cannot initialize a built-in module twice "
                          "in PyPy")
    return __import__(name)

def init_frozen(name):
    return None

def is_builtin(name):
    import sys
    if name in sys.builtin_module_names:
        return -1   # cannot be initialized again
    else:
        return 0

def is_frozen(name):
    return False


# ____________________________________________________________

try:
    # PyPy-specific interface: hint from the thread module to ask us to
    # provide an import lock
    from thread import _please_provide_import_lock
except ImportError:
    def lock_held():
        """On platforms without threads, return False."""
        return False
    def acquire_lock():
        """On platforms without threads, this function does nothing."""
    def release_lock():
        """On platforms without threads, this function does nothing."""

else:
    del _please_provide_import_lock
    import thread

    class _ImportLock:
        def __init__(self):
            self.lock = thread.allocate_lock()
            self.in_thread = None
            self.recursions = 0

        def held(self):
            """Return True if the import lock is currently held, else False."""
            return self.in_thread is not None

        def acquire(self):
            """Acquires the interpreter's import lock for the current thread.
            This lock should be used by import hooks to ensure thread-safety
            when importing modules.
            """
            myident = thread.get_ident()
            if self.in_thread == myident:
                self.recursions += 1
            else:
                self.lock.acquire()
                self.in_thread = myident
                self.recursions = 1

        def release(self):
            """Release the interpreter's import lock."""
            myident = thread.get_ident()
            if self.in_thread != myident:
                raise RuntimeError("not holding the import lock")
            self.recursions -= 1
            if self.recursions == 0:
                self.in_thread = None
                self.lock.release()

    _importlock = _ImportLock()

    lock_held    = _importlock.held
    acquire_lock = _importlock.acquire
    release_lock = _importlock.release

    import __builtin__
    _original_import_hook = __builtin__.__import__
    def __lockedimport__(modulename, globals=None, locals=None, fromlist=None):
        acquire_lock()
        try:
            return _original_import_hook(modulename, globals, locals, fromlist)
        finally:
            release_lock()
    __builtin__.__import__ = __lockedimport__
    del __builtin__
