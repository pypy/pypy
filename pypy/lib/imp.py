"""
This module provides the components needed to build your own
__import__ function.  Undocumented functions are obsolete.
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
    return '\x3b\xf2\x0d\x0a'

def get_suffixes():
    return [('.py', 'U', PY_SOURCE)]


def find_module(name, path=None):
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
    import sys, os
    new_module = type(sys)
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


try:
    # PyPy-specific interface: hint from the thread module to ask us to
    # provide an import lock
    from thread import _please_provide_import_lock
except ImportError:
    def lock_held():
        return False
    def acquire_lock():
        pass
    def release_lock():
        pass
else:
    del _please_provide_import_lock
    import thread

    class _ImportLock:
        def __init__(self):
            self.lock = thread.allocate_lock()
            self.in_thread = None
            self.recursions = 0

        def held(self):
            return self.in_thread is not None

        def acquire(self):
            myident = thread.get_ident()
            if self.in_thread == myident:
                self.recursions += 1
            else:
                self.lock.acquire()
                self.in_thread = myident
                self.recursions = 1

        def release(self):
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
