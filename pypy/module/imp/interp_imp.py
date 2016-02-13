from pypy.module.imp import importing
from rpython.rlib import streamio
from rpython.rlib.streamio import StreamErrors
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.module import Module
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pyparser import pyparse
from pypy.objspace.std import unicodeobject
from pypy.module._io.interp_iobase import W_IOBase
from pypy.module._io import interp_io
from pypy.interpreter.streamutil import wrap_streamerror


def get_suffixes(space):
    w = space.wrap
    suffixes_w = []
    if importing.has_so_extension(space):
        suffixes_w.append(
            space.newtuple([w(importing.get_so_extension(space)),
                            w('rb'), w(importing.C_EXTENSION)]))
    suffixes_w.extend([
        space.newtuple([w('.py'), w('U'), w(importing.PY_SOURCE)]),
        space.newtuple([w('.pyc'), w('rb'), w(importing.PY_COMPILED)]),
        ])
    return space.newlist(suffixes_w)

def extension_suffixes(space):
    suffixes_w = []
    if space.config.objspace.usemodules.cpyext:
        suffixes_w.append(space.wrap(importing.get_so_extension(space)))
    return space.newlist(suffixes_w)

def get_magic(space):
    x = importing.get_pyc_magic(space)
    a = x & 0xff
    x >>= 8
    b = x & 0xff
    x >>= 8
    c = x & 0xff
    x >>= 8
    d = x & 0xff
    return space.wrapbytes(chr(a) + chr(b) + chr(c) + chr(d))

def get_tag(space):
    """get_tag() -> string
    Return the magic tag for .pyc or .pyo files."""
    return space.wrap(importing.PYC_TAG)

def get_file(space, w_file, filename, filemode):
    if space.is_none(w_file):
        try:
            return streamio.open_file_as_stream(filename, filemode)
        except streamio.StreamErrors, e:
            # XXX this is not quite the correct place, but it will do for now.
            # XXX see the issue which I'm sure exists already but whose number
            # XXX I cannot find any more...
            raise wrap_streamerror(space, e)
    else:
        w_iobase = space.interp_w(W_IOBase, w_file)
        # XXX: not all W_IOBase have a fileno method: in that case, we should
        # probably raise a TypeError?
        fd = space.int_w(space.call_method(w_iobase, 'fileno'))
        return streamio.fdopen_as_stream(fd, filemode)

@unwrap_spec(filename='fsencode')
def load_dynamic(space, w_modulename, filename, w_file=None):
    if not importing.has_so_extension(space):
        raise OperationError(space.w_ImportError, space.wrap(
            "Not implemented"))

    # the next line is mandatory to init cpyext
    space.getbuiltinmodule("cpyext")

    from pypy.module.cpyext.api import load_extension_module
    load_extension_module(space, filename, space.str_w(w_modulename))

    return importing.check_sys_modules(space, w_modulename)

def new_module(space, w_name):
    return space.wrap(Module(space, w_name, add_package=False))

def init_builtin(space, w_name):
    name = space.str0_w(w_name)
    if name not in space.builtin_modules:
        return
    # force_init is needed to make reload actually reload instead of just
    # using the already-present module in sys.modules.
    reuse = space.finditem(space.sys.get('modules'), w_name) is not None
    return space.getbuiltinmodule(name, force_init=True, reuse=reuse)

def init_frozen(space, w_name):
    return None

def is_builtin(space, w_name):
    name = space.str0_w(w_name)
    if name not in space.builtin_modules:
        return space.wrap(0)
    if space.finditem(space.sys.get('modules'), w_name) is not None:
        return space.wrap(-1)   # cannot be initialized again
    return space.wrap(1)

def is_frozen(space, w_name):
    return space.w_False

def get_frozen_object(space, w_name):
    raise oefmt(space.w_ImportError,
                "No such frozen object named %R", w_name)

def is_frozen_package(space, w_name):
    raise oefmt(space.w_ImportError,
                "No such frozen object named %R", w_name)

#__________________________________________________________________

def lock_held(space):
    if space.config.objspace.usemodules.thread:
        return space.wrap(importing.getimportlock(space).lock_held_by_anyone())
    else:
        return space.w_False

def acquire_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).acquire_lock()

def release_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).release_lock(silent_after_fork=False)

def reinit_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).reinit_lock()

@unwrap_spec(pathname='fsencode')
def cache_from_source(space, pathname, w_debug_override=None):
    """cache_from_source(path, [debug_override]) -> path
    Given the path to a .py file, return the path to its .pyc/.pyo file.

    The .py file does not need to exist; this simply returns the path to the
    .pyc/.pyo file calculated as if the .py file were imported.  The extension
    will be .pyc unless __debug__ is not defined, then it will be .pyo.

    If debug_override is not None, then it must be a boolean and is taken as
    the value of __debug__ instead."""
    return space.fsdecode(space.wrapbytes(
            importing.make_compiled_pathname(pathname)))

@unwrap_spec(pathname='fsencode')
def source_from_cache(space, pathname):
    """source_from_cache(path) -> path
    Given the path to a .pyc./.pyo file, return the path to its .py file.

    The .pyc/.pyo file does not need to exist; this simply returns the path to
    the .py file calculated to correspond to the .pyc/.pyo file.  If path
    does not conform to PEP 3147 format, ValueError will be raised."""
    sourcename = importing.make_source_pathname(pathname)
    if sourcename is None:
        raise oefmt(space.w_ValueError,
                    "Not a PEP 3147 pyc path: %s", pathname)
    return space.fsdecode(space.wrapbytes(sourcename))

@unwrap_spec(pathname='fsencode')
def fix_co_filename(space, w_code, pathname):
    code_w = space.interp_w(PyCode, w_code)
    importing.update_code_filenames(space, code_w, pathname)


