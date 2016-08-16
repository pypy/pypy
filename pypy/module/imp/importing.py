"""
Implementation of the interpreter-level default import logic.
"""

import sys, os, stat

from pypy.interpreter.module import Module
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, generic_new_descr
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root, CannotHaveLock
from pypy.interpreter.eval import Code
from pypy.interpreter.pycode import PyCode
from rpython.rlib import streamio, jit
from rpython.rlib.streamio import StreamErrors
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.signature import signature
from rpython.rlib import rposix_stat, types
from pypy.module.sys.version import PYPY_VERSION

_WIN32 = sys.platform == 'win32'

SO = '.pyd' if _WIN32 else '.so'
PREFIX = 'pypy3-'
DEFAULT_SOABI = '%s%d%d' % ((PREFIX,) + PYPY_VERSION[:2])

PYC_TAG = '%s%d%d' % ((PREFIX,) + PYPY_VERSION[:2])

@specialize.memo()
def get_so_extension(space):
    if space.config.objspace.soabi is not None:
        soabi = space.config.objspace.soabi
    else:
        soabi = DEFAULT_SOABI

    if not soabi:
        return SO

    if not space.config.translating:
        soabi += 'i'

    return '.' + soabi + SO

def log_pyverbose(space, level, message):
    if space.sys.w_initialdict is None:
        return # sys module not initialised, avoid recursion
    verbose = space.sys.get_flag('verbose')
    if verbose >= level:
        w_stderr = space.sys.get('stderr')
        space.call_method(w_stderr, "write", space.wrap(message))

def has_so_extension(space):
    return (space.config.objspace.usemodules.cpyext or
            space.config.objspace.usemodules._cffi_backend)

def check_sys_modules(space, w_modulename):
    return space.finditem(space.sys.get('modules'), w_modulename)

def check_sys_modules_w(space, modulename):
    return space.finditem_str(space.sys.get('modules'), modulename)


lib_pypy = os.path.join(os.path.dirname(__file__),
                        '..', '..', '..', 'lib_pypy')

@unwrap_spec(modulename='str0', level=int)
def importhook(space, modulename, w_globals=None, w_locals=None, w_fromlist=None, level=0):
    # A minimal version, that can only import builtin and lib_pypy modules!
    assert w_locals is w_globals
    assert level == 0

    w_mod = check_sys_modules_w(space, modulename)
    if w_mod:
        return w_mod
    lock = getimportlock(space)
    try:
        lock.acquire_lock()

        if modulename in space.builtin_modules:
            return space.getbuiltinmodule(modulename)

        ec = space.getexecutioncontext()
        with open(os.path.join(lib_pypy, modulename + '.py')) as fp:
            source = fp.read()
        pathname = "<frozen %s>" % modulename
        code_w = ec.compiler.compile(source, pathname, 'exec', 0)
        w_mod = add_module(space, space.wrap(modulename))
        assert isinstance(w_mod, Module) # XXX why is that necessary?
        space.setitem(space.sys.get('modules'), w_mod.w_name, w_mod)
        space.setitem(w_mod.w_dict, space.wrap('__name__'), w_mod.w_name)
        code_w.exec_code(space, w_mod.w_dict, w_mod.w_dict)
        assert check_sys_modules_w(space, modulename)
    finally:
        lock.release_lock(silent_after_fork=True)
    return w_mod


class _WIN32Path(object):
    def __init__(self, path):
        self.path = path

    def as_unicode(self):
        return self.path

def _prepare_module(space, w_mod, filename, pkgdir):
    w = space.wrap
    space.sys.setmodule(w_mod)
    space.setattr(w_mod, w('__file__'), space.wrap(filename))
    space.setattr(w_mod, w('__doc__'), space.w_None)
    if pkgdir is not None:
        space.setattr(w_mod, w('__path__'), space.newlist([w(pkgdir)]))

def add_module(space, w_name):
    w_mod = check_sys_modules(space, w_name)
    if w_mod is None:
        w_mod = space.wrap(Module(space, w_name))
        space.sys.setmodule(w_mod)
    return w_mod

def load_c_extension(space, filename, modulename):
    from pypy.module.cpyext.api import load_extension_module
    log_pyverbose(space, 1, "import %s # from %s\n" %
                  (modulename, filename))
    load_extension_module(space, filename, modulename)
    # NB. cpyext.api.load_extension_module() can also delegate to _cffi_backend

# __________________________________________________________________
#
# import lock, to prevent two threads from running module-level code in
# parallel.  This behavior is more or less part of the language specs,
# as an attempt to avoid failure of 'from x import y' if module x is
# still being executed in another thread.

# This logic is tested in pypy.module.thread.test.test_import_lock.

class ImportRLock:

    def __init__(self, space):
        self.space = space
        self.lock = None
        self.lockowner = None
        self.lockcounter = 0

    def lock_held_by_someone_else(self):
        me = self.space.getexecutioncontext()   # used as thread ident
        return self.lockowner is not None and self.lockowner is not me

    def lock_held_by_anyone(self):
        return self.lockowner is not None

    def acquire_lock(self):
        # this function runs with the GIL acquired so there is no race
        # condition in the creation of the lock
        if self.lock is None:
            try:
                self.lock = self.space.allocate_lock()
            except CannotHaveLock:
                return
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.lockowner is me:
            pass    # already acquired by the current thread
        else:
            self.lock.acquire(True)
            assert self.lockowner is None
            assert self.lockcounter == 0
            self.lockowner = me
        self.lockcounter += 1

    def release_lock(self, silent_after_fork):
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.lockowner is not me:
            if self.lockowner is None and silent_after_fork:
                # Too bad.  This situation can occur if a fork() occurred
                # with the import lock held, and we're the child.
                return
            if self.lock is None:   # CannotHaveLock occurred
                return
            space = self.space
            raise oefmt(space.w_RuntimeError, "not holding the import lock")
        assert self.lockcounter > 0
        self.lockcounter -= 1
        if self.lockcounter == 0:
            self.lockowner = None
            self.lock.release()

    def reinit_lock(self):
        # Called after fork() to ensure that newly created child
        # processes do not share locks with the parent
        if self.lockcounter > 1:
            # Forked as a side effect of import
            self.lock = self.space.allocate_lock()
            me = self.space.getexecutioncontext()
            self.lock.acquire(True)
            # XXX: can the previous line fail?
            self.lockowner = me
            self.lockcounter -= 1
        else:
            self.lock = None
            self.lockowner = None
            self.lockcounter = 0

def getimportlock(space):
    return space.fromcache(ImportRLock)

# __________________________________________________________________
#
# .pyc file support

"""
   Magic word to reject .pyc files generated by other Python versions.
   It should change for each incompatible change to the bytecode.

   The value of CR and LF is incorporated so if you ever read or write
   a .pyc file in text mode the magic number will be wrong; also, the
   Apple MPW compiler swaps their values, botching string constants.

   CPython 2 uses values between 20121 - 62xxx
   CPython 3 uses values greater than 3000
   PyPy uses values under 3000

"""

# Depending on which opcodes are enabled, eg. CALL_METHOD we bump the version
# number by some constant
#
#     CPython + 0                  -- used by CPython without the -U option
#     CPython + 1                  -- used by CPython with the -U option
#     CPython + 7 = default_magic  -- used by PyPy (incompatible!)
#
from pypy.interpreter.pycode import default_magic
MARSHAL_VERSION_FOR_PYC = 2

def get_pyc_magic(space):
    return default_magic


def parse_source_module(space, pathname, source):
    """ Parse a source file and return the corresponding code object """
    ec = space.getexecutioncontext()
    pycode = ec.compiler.compile(source, pathname, 'exec', 0)
    return pycode

def exec_code_module(space, w_mod, code_w, pathname, cpathname,
                     write_paths=True):
    w_dict = space.getattr(w_mod, space.wrap('__dict__'))
    space.call_method(w_dict, 'setdefault',
                      space.wrap('__builtins__'),
                      space.wrap(space.builtin))
    if write_paths:
        if pathname is not None:
            w_pathname = get_sourcefile(space, pathname)
        else:
            w_pathname = space.wrap(code_w.co_filename)
        space.setitem(w_dict, space.wrap("__file__"), w_pathname)
        space.setitem(w_dict, space.wrap("__cached__"), space.wrap(cpathname))
    code_w.exec_code(space, w_dict, w_dict)

def rightmost_sep(filename):
    "Like filename.rfind('/'), but also search for \\."
    index = filename.rfind(os.sep)
    if os.altsep is not None:
        index2 = filename.rfind(os.altsep)
        index = max(index, index2)
    return index

@signature(types.str0(), returns=types.str0())
def make_compiled_pathname(pathname):
    "Given the path to a .py file, return the path to its .pyc file."
    # foo.py -> __pycache__/foo.<tag>.pyc

    lastpos = rightmost_sep(pathname) + 1
    assert lastpos >= 0  # zero when slash, takes the full name
    fname = pathname[lastpos:]
    if lastpos > 0:
        # Windows: re-use the last separator character (/ or \\) when
        # appending the __pycache__ path.
        lastsep = pathname[lastpos-1]
    else:
        lastsep = os.sep
    ext = fname
    for i in range(len(fname)):
        if fname[i] == '.':
            ext = fname[:i + 1]

    result = (pathname[:lastpos] + "__pycache__" + lastsep +
              ext + PYC_TAG + '.pyc')
    return result

#@signature(types.str0(), returns=types.str0())
def make_source_pathname(pathname):
    "Given the path to a .pyc file, return the path to its .py file."
    # (...)/__pycache__/foo.<tag>.pyc -> (...)/foo.py

    right = rightmost_sep(pathname)
    if right < 0:
        return None
    left = rightmost_sep(pathname[:right]) + 1
    assert left >= 0
    if pathname[left:right] != '__pycache__':
        return None

    # Now verify that the path component to the right of the last
    # slash has two dots in it.
    rightpart = pathname[right + 1:]
    dot0 = rightpart.find('.') + 1
    if dot0 <= 0:
        return None
    dot1 = rightpart[dot0:].find('.') + 1
    if dot1 <= 0:
        return None
    # Too many dots?
    if rightpart[dot0 + dot1:].find('.') >= 0:
        return None

    result = pathname[:left] + rightpart[:dot0] + 'py'
    return result

def get_sourcefile(space, filename):
    start = len(filename) - 4
    stop = len(filename) - 1
    if not 0 <= start <= stop or filename[start:stop].lower() != ".py":
        return space.wrap_fsdecoded(filename)
    py = make_source_pathname(filename)
    if py is None:
        py = filename[:-1]
    try:
        st = os.stat(py)
    except OSError:
        pass
    else:
        if stat.S_ISREG(st.st_mode):
            return space.wrap_fsdecoded(py)
    return space.wrap_fsdecoded(filename)

def update_code_filenames(space, code_w, pathname, oldname=None):
    assert isinstance(code_w, PyCode)
    if oldname is None:
        oldname = code_w.co_filename
    elif code_w.co_filename != oldname:
        return

    code_w.co_filename = pathname
    constants = code_w.co_consts_w
    for const in constants:
        if const is not None and isinstance(const, PyCode):
            update_code_filenames(space, const, pathname, oldname)

def _get_long(s):
    a = ord(s[0])
    b = ord(s[1])
    c = ord(s[2])
    d = ord(s[3])
    if d >= 0x80:
        d -= 0x100
    return a | (b<<8) | (c<<16) | (d<<24)

def read_compiled_module(space, cpathname, strbuf):
    """ Read a code object from a file and check it for validity """

    w_marshal = space.getbuiltinmodule('marshal')
    w_code = space.call_method(w_marshal, 'loads', space.newbytes(strbuf))
    if not isinstance(w_code, Code):
        raise oefmt(space.w_ImportError, "Non-code object in %s", cpathname)
    return w_code

@jit.dont_look_inside
def load_compiled_module(space, w_modulename, w_mod, cpathname, magic,
                         timestamp, source, write_paths=True):
    """
    Load a module from a compiled file, execute it, and return its
    module object.
    """
    log_pyverbose(space, 1, "import %s # compiled from %s\n" %
                  (space.str_w(w_modulename), cpathname))

    if magic != get_pyc_magic(space):
        raise oefmt(space.w_ImportError, "Bad magic number in %s", cpathname)
    #print "loading pyc file:", cpathname
    code_w = read_compiled_module(space, cpathname, source)
    try:
        optimize = space.sys.get_flag('optimize')
    except RuntimeError:
        # during bootstrapping
        optimize = 0
    if optimize >= 2:
        code_w.remove_docstrings(space)

    exec_code_module(space, w_mod, code_w, cpathname, cpathname, write_paths)

    return w_mod
