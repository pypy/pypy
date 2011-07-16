from pypy.module.imp import importing
from pypy.module._file.interp_file import W_File
from pypy.rlib import streamio
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.module import Module
from pypy.interpreter.gateway import unwrap_spec
from pypy.module._file.interp_stream import StreamErrors, wrap_streamerror


def get_suffixes(space):
    w = space.wrap
    suffixes_w = []
    if space.config.objspace.usemodules.cpyext:
        suffixes_w.append(
            space.newtuple([w(importing.get_so_extension(space)),
                            w('rb'), w(importing.C_EXTENSION)]))
    suffixes_w.extend([
        space.newtuple([w('.py'), w('U'), w(importing.PY_SOURCE)]),
        space.newtuple([w('.pyc'), w('rb'), w(importing.PY_COMPILED)]),
        ])
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
    return space.wrap(chr(a) + chr(b) + chr(c) + chr(d))

def get_file(space, w_file, filename, filemode):
    if w_file is None or space.is_w(w_file, space.w_None):
        try:
            return streamio.open_file_as_stream(filename, filemode)
        except StreamErrors, e:
            # XXX this is not quite the correct place, but it will do for now.
            # XXX see the issue which I'm sure exists already but whose number
            # XXX I cannot find any more...
            raise wrap_streamerror(space, e)
    else:
        return space.interp_w(W_File, w_file).stream

def find_module(space, w_name, w_path=None):
    name = space.str_w(w_name)
    if space.is_w(w_path, space.w_None):
        w_path = None

    find_info = importing.find_module(
        space, name, w_name, name, w_path, use_loader=False)
    if not find_info:
        raise operationerrfmt(
            space.w_ImportError,
            "No module named %s", name)

    w_filename = space.wrap(find_info.filename)
    stream = find_info.stream

    if stream is not None:
        fileobj = W_File(space)
        fileobj.fdopenstream(
            stream, stream.try_to_find_file_descriptor(),
            find_info.filemode, w_filename)
        w_fileobj = space.wrap(fileobj)
    else:
        w_fileobj = space.w_None
    w_import_info = space.newtuple(
        [space.wrap(find_info.suffix),
         space.wrap(find_info.filemode),
         space.wrap(find_info.modtype)])
    return space.newtuple([w_fileobj, w_filename, w_import_info])

def load_module(space, w_name, w_file, w_filename, w_info):
    w_suffix, w_filemode, w_modtype = space.unpackiterable(w_info)

    filename = space.str_w(w_filename)
    filemode = space.str_w(w_filemode)
    if space.is_w(w_file, space.w_None):
        stream = None
    else:
        stream = get_file(space, w_file, filename, filemode)

    find_info = importing.FindInfo(
        space.int_w(w_modtype),
        filename,
        stream,
        space.str_w(w_suffix),
        filemode)
    return importing.load_module(
        space, w_name, find_info, reuse=True)

def load_source(space, w_modulename, w_filename, w_file=None):
    filename = space.str_w(w_filename)

    stream = get_file(space, w_file, filename, 'U')

    w_mod = space.wrap(Module(space, w_modulename))
    importing._prepare_module(space, w_mod, filename, None)

    importing.load_source_module(
        space, w_modulename, w_mod, filename, stream.readall())
    if space.is_w(w_file, space.w_None):
        stream.close()
    return w_mod

@unwrap_spec(filename=str)
def _run_compiled_module(space, w_modulename, filename, w_file, w_module):
    # the function 'imp._run_compiled_module' is a pypy-only extension
    stream = get_file(space, w_file, filename, 'rb')

    magic = importing._r_long(stream)
    timestamp = importing._r_long(stream)

    importing.load_compiled_module(
        space, w_modulename, w_module, filename, magic, timestamp,
        stream.readall())
    if space.is_w(w_file, space.w_None):
        stream.close()

@unwrap_spec(filename=str)
def load_compiled(space, w_modulename, filename, w_file=None):
    w_mod = space.wrap(Module(space, w_modulename))
    importing._prepare_module(space, w_mod, filename, None)
    _run_compiled_module(space, w_modulename, filename, w_file, w_mod)
    return w_mod

@unwrap_spec(filename=str)
def load_dynamic(space, w_modulename, filename, w_file=None):
    if not space.config.objspace.usemodules.cpyext:
        raise OperationError(space.w_ImportError, space.wrap(
            "Not implemented"))
    importing.load_c_extension(space, filename, space.str_w(w_modulename))
    return importing.check_sys_modules(space, w_modulename)

def new_module(space, w_name):
    return space.wrap(Module(space, w_name, add_package=False))

def init_builtin(space, w_name):
    name = space.str_w(w_name)
    if name not in space.builtin_modules:
        return
    if space.finditem(space.sys.get('modules'), w_name) is not None:
        raise OperationError(
            space.w_ImportError,
            space.wrap("cannot initialize a built-in module twice in PyPy"))
    return space.getbuiltinmodule(name)

def init_frozen(space, w_name):
    return None

def is_builtin(space, w_name):
    name = space.str_w(w_name)
    if name not in space.builtin_modules:
        return space.wrap(0)
    if space.finditem(space.sys.get('modules'), w_name) is not None:
        return space.wrap(-1)   # cannot be initialized again
    return space.wrap(1)

def is_frozen(space, w_name):
    return space.w_False

#__________________________________________________________________

def lock_held(space):
    if space.config.objspace.usemodules.thread:
        return space.wrap(importing.getimportlock(space).lock_held())
    else:
        return space.w_False

def acquire_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).acquire_lock()

def release_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).release_lock()

def reinit_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).reinit_lock()
