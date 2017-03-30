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
from pypy.module.sys.version import PYPY_VERSION

_WIN32 = sys.platform == 'win32'

SEARCH_ERROR = 0
PY_SOURCE = 1
PY_COMPILED = 2
C_EXTENSION = 3
# PY_RESOURCE = 4
PKG_DIRECTORY = 5
C_BUILTIN = 6
PY_FROZEN = 7
# PY_CODERESOURCE = 8
IMP_HOOK = 9

SO = '.pyd' if _WIN32 else '.so'

# this used to change for every minor version, but no longer does: there
# is little point any more, as the so's tend to be cross-version-
# compatible, more so than between various versions of CPython.  Be
# careful if we need to update it again: it is now used for both cpyext
# and cffi so's.  If we do have to update it, we'd likely need a way to
# split the two usages again.
#DEFAULT_SOABI = 'pypy-%d%d' % PYPY_VERSION[:2]
DEFAULT_SOABI = 'pypy-41'

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
        space.call_method(w_stderr, "write", space.newtext(message))

def file_exists(path):
    "Test whether the given path is an existing regular file."
    return os.path.isfile(path) and case_ok(path)

def path_exists(path):
    "Test whether the given path exists."
    return os.path.exists(path) and case_ok(path)

def has_so_extension(space):
    return (space.config.objspace.usemodules.cpyext or
            space.config.objspace.usemodules._cffi_backend)

def has_init_module(space, filepart):
    "Return True if the directory filepart qualifies as a package."
    init = os.path.join(filepart, "__init__")
    if path_exists(init + ".py"):
        return True
    if space.config.objspace.lonepycfiles and path_exists(init + ".pyc"):
        return True
    return False

def find_modtype(space, filepart):
    """Check which kind of module to import for the given filepart,
    which is a path without extension.  Returns PY_SOURCE, PY_COMPILED or
    SEARCH_ERROR.
    """
    # check the .py file
    pyfile = filepart + ".py"
    if file_exists(pyfile):
        return PY_SOURCE, ".py", "U"

    # on Windows, also check for a .pyw file
    if _WIN32:
        pyfile = filepart + ".pyw"
        if file_exists(pyfile):
            return PY_SOURCE, ".pyw", "U"

    # The .py file does not exist.  By default on PyPy, lonepycfiles
    # is False: if a .py file does not exist, we don't even try to
    # look for a lone .pyc file.
    # The "imp" module does not respect this, and is allowed to find
    # lone .pyc files.
    # check the .pyc file
    if space.config.objspace.lonepycfiles:
        pycfile = filepart + ".pyc"
        if file_exists(pycfile):
            # existing .pyc file
            return PY_COMPILED, ".pyc", "rb"

    if has_so_extension(space):
        so_extension = get_so_extension(space)
        pydfile = filepart + so_extension
        if file_exists(pydfile):
            return C_EXTENSION, so_extension, "rb"

    return SEARCH_ERROR, None, None

if sys.platform.startswith('linux') or 'freebsd' in sys.platform:
    def case_ok(filename):
        return True
else:
    # XXX that's slow
    def case_ok(filename):
        index = filename.rfind(os.sep)
        if os.altsep is not None:
            index2 = filename.rfind(os.altsep)
            index = max(index, index2)
        if index < 0:
            directory = os.curdir
        else:
            directory = filename[:index+1]
            filename = filename[index+1:]
        try:
            return filename in os.listdir(directory)
        except OSError:
            return False

def try_getattr(space, w_obj, w_name):
    try:
        return space.getattr(w_obj, w_name)
    except OperationError:
        # ugh, but blame CPython :-/ this is supposed to emulate
        # hasattr, which eats all exceptions.
        return None

def check_sys_modules(space, w_modulename):
    return space.finditem(space.sys.get('modules'), w_modulename)

def check_sys_modules_w(space, modulename):
    return space.finditem_str(space.sys.get('modules'), modulename)

@jit.elidable
def _get_dot_position(str, n):
    # return the index in str of the '.' such that there are n '.'-separated
    # strings after it
    result = len(str)
    while n > 0 and result >= 0:
        n -= 1
        result = str.rfind('.', 0, result)
    return result

def _get_relative_name(space, modulename, level, w_globals):
    ctxt_w_package = space.finditem_str(w_globals, '__package__')
    ctxt_w_package = jit.promote(ctxt_w_package)
    level = jit.promote(level)

    ctxt_package = None
    if ctxt_w_package is not None and ctxt_w_package is not space.w_None:
        try:
            ctxt_package = space.text0_w(ctxt_w_package)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
            raise oefmt(space.w_ValueError, "__package__ set to non-string")

    if ctxt_package is not None:
        # __package__ is set, so use it
        if ctxt_package == '' and level < 0:
            return None, 0

        dot_position = _get_dot_position(ctxt_package, level - 1)
        if dot_position < 0:
            if len(ctxt_package) == 0:
                where = "in non-package"
            else:
                where = "beyond toplevel package"
            raise oefmt(space.w_ValueError,
                        "Attempted relative import %s", where)

        # Try to import parent package
        try:
            absolute_import(space, ctxt_package, 0, None, tentative=False)
        except OperationError as e:
            if not e.match(space, space.w_ImportError):
                raise
            if level > 0:
                raise oefmt(space.w_SystemError,
                            "Parent module '%s' not loaded, cannot perform "
                            "relative import", ctxt_package)
            else:
                msg = ("Parent module '%s' not found while handling absolute "
                       "import" % ctxt_package)
                space.warn(space.newtext(msg), space.w_RuntimeWarning)

        rel_modulename = ctxt_package[:dot_position]
        rel_level = rel_modulename.count('.') + 1
        if modulename:
            rel_modulename += '.' + modulename
    else:
        # __package__ not set, so figure it out and set it
        ctxt_w_name = space.finditem_str(w_globals, '__name__')
        ctxt_w_path = space.finditem_str(w_globals, '__path__')

        ctxt_w_name = jit.promote(ctxt_w_name)
        ctxt_name = None
        if ctxt_w_name is not None:
            try:
                ctxt_name = space.text0_w(ctxt_w_name)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise

        if not ctxt_name:
            return None, 0

        m = max(level - 1, 0)
        if ctxt_w_path is None:   # plain module
            m += 1
        dot_position = _get_dot_position(ctxt_name, m)
        if dot_position < 0:
            if level > 0:
                raise oefmt(space.w_ValueError,
                            "Attempted relative import in non-package")
            rel_modulename = ''
            rel_level = 0
        else:
            rel_modulename = ctxt_name[:dot_position]
            rel_level = rel_modulename.count('.') + 1

        if ctxt_w_path is not None:
            # __path__ is set, so __name__ is already the package name
            space.setitem(w_globals, space.newtext("__package__"), ctxt_w_name)
        else:
            # Normal module, so work out the package name if any
            last_dot_position = ctxt_name.rfind('.')
            if last_dot_position < 0:
                space.setitem(w_globals, space.newtext("__package__"), space.w_None)
            else:
                space.setitem(w_globals, space.newtext("__package__"),
                              space.newtext(ctxt_name[:last_dot_position]))

        if modulename:
            if rel_modulename:
                rel_modulename += '.' + modulename
            else:
                rel_modulename = modulename

    return rel_modulename, rel_level


@unwrap_spec(name='text0', level=int)
def importhook(space, name, w_globals=None,
               w_locals=None, w_fromlist=None, level=-1):
    modulename = name
    if not modulename and level < 0:
        raise oefmt(space.w_ValueError, "Empty module name")

    if w_fromlist is not None and not space.is_true(w_fromlist):
        w_fromlist = None

    rel_modulename = None
    if (level != 0 and w_globals is not None and
            space.isinstance_w(w_globals, space.w_dict)):
        rel_modulename, rel_level = _get_relative_name(space, modulename, level,
                                                       w_globals)
        if rel_modulename:
            # if no level was set, ignore import errors, and
            # fall back to absolute import at the end of the
            # function.
            if level == -1:
                # This check is a fast path to avoid redoing the
                # following absolute_import() in the common case
                w_mod = check_sys_modules_w(space, rel_modulename)
                if w_mod is not None and space.is_w(w_mod, space.w_None):
                    # if we already find space.w_None, it means that we
                    # already tried and failed and fell back to the
                    # end of this function.
                    w_mod = None
                else:
                    w_mod = absolute_import(space, rel_modulename, rel_level,
                                            w_fromlist, tentative=True)
            else:
                w_mod = absolute_import(space, rel_modulename, rel_level,
                                        w_fromlist, tentative=False)
            if w_mod is not None:
                return w_mod

    w_mod = absolute_import(space, modulename, 0, w_fromlist, tentative=0)
    if rel_modulename is not None:
        space.setitem(space.sys.get('modules'), space.newtext(rel_modulename), space.w_None)
    return w_mod

def absolute_import(space, modulename, baselevel, w_fromlist, tentative):
    # Short path: check in sys.modules, but only if there is no conflict
    # on the import lock.  In the situation of 'import' statements
    # inside tight loops, this should be true, and absolute_import_try()
    # should be followed by the JIT and turned into not much code.  But
    # if the import lock is currently held by another thread, then we
    # have to wait, and so shouldn't use the fast path.
    if not getimportlock(space).lock_held_by_someone_else():
        w_mod = absolute_import_try(space, modulename, baselevel, w_fromlist)
        if w_mod is not None and not space.is_w(w_mod, space.w_None):
            return w_mod
    return absolute_import_with_lock(space, modulename, baselevel,
                                     w_fromlist, tentative)

@jit.dont_look_inside
def absolute_import_with_lock(space, modulename, baselevel,
                              w_fromlist, tentative):
    lock = getimportlock(space)
    lock.acquire_lock()
    try:
        return _absolute_import(space, modulename, baselevel,
                                w_fromlist, tentative)
    finally:
        lock.release_lock(silent_after_fork=True)

@jit.unroll_safe
def absolute_import_try(space, modulename, baselevel, w_fromlist):
    """ Only look up sys.modules, not actually try to load anything
    """
    w_path = None
    last_dot = 0
    if '.' not in modulename:
        w_mod = check_sys_modules_w(space, modulename)
        first = w_mod
        if w_fromlist is not None and w_mod is not None:
            w_path = try_getattr(space, w_mod, space.newtext('__path__'))
    else:
        level = 0
        first = None
        while last_dot >= 0:
            last_dot = modulename.find('.', last_dot + 1)
            if last_dot < 0:
                w_mod = check_sys_modules_w(space, modulename)
            else:
                w_mod = check_sys_modules_w(space, modulename[:last_dot])
            if w_mod is None or space.is_w(w_mod, space.w_None):
                return None
            if level == baselevel:
                first = w_mod
            if w_fromlist is not None:
                w_path = try_getattr(space, w_mod, space.newtext('__path__'))
            level += 1
    if w_fromlist is not None:
        # bit artificial code but important to not just unwrap w_fromlist
        # to get a better trace. if it is unwrapped, the immutability of the
        # tuple is lost
        length = space.len_w(w_fromlist)
        if w_path is not None:
            if length == 1 and space.eq_w(
                    space.getitem(w_fromlist, space.newint(0)),
                    space.newtext('*')):
                w_all = try_getattr(space, w_mod, space.newtext('__all__'))
                if w_all is not None:
                    w_fromlist = w_all
                    length = space.len_w(w_fromlist)
                else:
                    w_fromlist = None
                    # "from x import *" with x already imported and no x.__all__
                    # always succeeds without doing more imports.  It will
                    # just copy everything from x.__dict__ as it is now.

            if w_fromlist is not None:
                for i in range(length):
                    w_name = space.getitem(w_fromlist, space.newint(i))
                    if not space.isinstance_w(w_name, space.w_text):
                        raise oefmt(space.w_TypeError,
                            "'Item in ``fromlist'' not a string")
                    if try_getattr(space, w_mod, w_name) is None:
                        return None
        return w_mod
    return first

def _absolute_import(space, modulename, baselevel, w_fromlist, tentative):
    if '/' in modulename or '\\' in modulename:
        raise oefmt(space.w_ImportError,
                    "Import by filename is not supported.")

    w_mod = None
    parts = modulename.split('.')
    prefix = []
    w_path = None

    first = None
    level = 0

    for part in parts:
        w_mod = load_part(space, w_path, prefix, part, w_mod,
                          tentative=tentative)
        if w_mod is None:
            return None

        if baselevel == level:
            first = w_mod
            tentative = 0
        prefix.append(part)
        w_path = try_getattr(space, w_mod, space.newtext('__path__'))
        level += 1

    if w_fromlist is not None:
        if w_path is not None:
            length = space.len_w(w_fromlist)
            if length == 1 and space.eq_w(
                    space.getitem(w_fromlist, space.newint(0)),
                    space.newtext('*')):
                w_all = try_getattr(space, w_mod, space.newtext('__all__'))
                if w_all is not None:
                    w_fromlist = w_all
                    length = space.len_w(w_fromlist)
                else:
                    w_fromlist = None
            if w_fromlist is not None:
                for i in range(length):
                    w_name = space.getitem(w_fromlist, space.newint(i))
                    if not space.isinstance_w(w_name, space.w_text):
                        raise oefmt(space.w_TypeError,
                            "'Item in ``fromlist'' not a string")
                    if try_getattr(space, w_mod, w_name) is None:
                        load_part(space, w_path, prefix, space.text0_w(w_name),
                                  w_mod, tentative=1)
        return w_mod
    else:
        return first

def find_in_meta_path(space, w_modulename, w_path):
    assert w_modulename is not None
    if w_path is None:
        w_path = space.w_None
    for w_hook in space.unpackiterable(space.sys.get("meta_path")):
        w_loader = space.call_method(w_hook, "find_module",
                                     w_modulename, w_path)
        if space.is_true(w_loader):
            return w_loader

def _getimporter(space, w_pathitem):
    # the function 'imp._getimporter' is a pypy-only extension
    w_path_importer_cache = space.sys.get("path_importer_cache")
    w_importer = space.finditem(w_path_importer_cache, w_pathitem)
    if w_importer is None:
        space.setitem(w_path_importer_cache, w_pathitem, space.w_None)
        for w_hook in space.unpackiterable(space.sys.get("path_hooks")):
            try:
                w_importer = space.call_function(w_hook, w_pathitem)
            except OperationError as e:
                if not e.match(space, space.w_ImportError):
                    raise
            else:
                break
        if w_importer is None:
            try:
                w_importer = space.call_function(
                    space.gettypefor(W_NullImporter), w_pathitem
                )
            except OperationError as e:
                if e.match(space, space.w_ImportError):
                    return None
                raise
        if space.is_true(w_importer):
            space.setitem(w_path_importer_cache, w_pathitem, w_importer)
    return w_importer

def find_in_path_hooks(space, w_modulename, w_pathitem):
    w_importer = _getimporter(space, w_pathitem)
    if w_importer is not None and space.is_true(w_importer):
        try:
            w_loader = space.call_method(w_importer, "find_module", w_modulename)
        except OperationError as e:
            if e.match(space, space.w_ImportError):
                return None
            raise
        if space.is_true(w_loader):
            return w_loader


class W_NullImporter(W_Root):
    def __init__(self, space):
        pass

    @unwrap_spec(path='fsencode')
    def descr_init(self, space, path):
        if not path:
            raise oefmt(space.w_ImportError, "empty pathname")

        # Directory should not exist
        try:
            st = os.stat(path)
        except OSError:
            pass
        else:
            if stat.S_ISDIR(st.st_mode):
                raise oefmt(space.w_ImportError, "existing directory")

    def find_module_w(self, space, __args__):
        return space.w_None

W_NullImporter.typedef = TypeDef(
    'imp.NullImporter',
    __new__=generic_new_descr(W_NullImporter),
    __init__=interp2app(W_NullImporter.descr_init),
    find_module=interp2app(W_NullImporter.find_module_w),
    )

class FindInfo:
    def __init__(self, modtype, filename, stream,
                 suffix="", filemode="", w_loader=None):
        self.modtype = modtype
        self.filename = filename
        self.stream = stream
        self.suffix = suffix
        self.filemode = filemode
        self.w_loader = w_loader

    @staticmethod
    def fromLoader(w_loader):
        return FindInfo(IMP_HOOK, '', None, w_loader=w_loader)

def find_module(space, modulename, w_modulename, partname, w_path,
                use_loader=True):
    # Examin importhooks (PEP302) before doing the import
    if use_loader:
        w_loader  = find_in_meta_path(space, w_modulename, w_path)
        if w_loader:
            return FindInfo.fromLoader(w_loader)

    # XXX Check for frozen modules?
    #     when w_path is a string

    delayed_builtin = None
    w_lib_extensions = None

    if w_path is None:
        # check the builtin modules
        if modulename in space.builtin_modules:
            delayed_builtin = FindInfo(C_BUILTIN, modulename, None)
            # a "real builtin module xx" shadows every file "xx.py" there
            # could possibly be; a "pseudo-extension module" does not, and
            # is only loaded at the point in sys.path where we find
            # '.../lib_pypy/__extensions__'.
            if modulename in space.MODULES_THAT_ALWAYS_SHADOW:
                return delayed_builtin
            w_lib_extensions = space.sys.get_state(space).w_lib_extensions
        w_path = space.sys.get('path')

    # XXX check frozen modules?
    #     when w_path is null

    if w_path is not None:
        for w_pathitem in space.unpackiterable(w_path):
            # sys.path_hooks import hook
            if (w_lib_extensions is not None and
                    space.eq_w(w_pathitem, w_lib_extensions)):
                return delayed_builtin
            if use_loader:
                w_loader = find_in_path_hooks(space, w_modulename, w_pathitem)
                if w_loader:
                    return FindInfo.fromLoader(w_loader)

            path = space.fsencode_w(w_pathitem)
            filepart = os.path.join(path, partname)
            log_pyverbose(space, 2, "# trying %s\n" % (filepart,))
            if os.path.isdir(filepart) and case_ok(filepart):
                if has_init_module(space, filepart):
                    return FindInfo(PKG_DIRECTORY, filepart, None)
                else:
                    msg = ("Not importing directory '%s' missing __init__.py" %
                           (filepart,))
                    space.warn(space.newtext(msg), space.w_ImportWarning)
            modtype, suffix, filemode = find_modtype(space, filepart)
            try:
                if modtype in (PY_SOURCE, PY_COMPILED, C_EXTENSION):
                    assert suffix is not None
                    filename = filepart + suffix
                    stream = streamio.open_file_as_stream(filename, filemode)
                    try:
                        return FindInfo(modtype, filename, stream, suffix, filemode)
                    except:
                        stream.close()
                        raise
            except StreamErrors:
                pass   # XXX! must not eat all exceptions, e.g.
                       # Out of file descriptors.

    # not found
    return delayed_builtin

def _prepare_module(space, w_mod, filename, pkgdir):
    space.sys.setmodule(w_mod)
    space.setattr(w_mod, space.newtext('__file__'), space.newtext(filename))
    space.setattr(w_mod, space.newtext('__doc__'), space.w_None)
    if pkgdir is not None:
        space.setattr(w_mod, space.newtext('__path__'), space.newlist([space.newtext(pkgdir)]))

def add_module(space, w_name):
    w_mod = check_sys_modules(space, w_name)
    if w_mod is None:
        w_mod = Module(space, w_name)
        space.sys.setmodule(w_mod)
    return w_mod

def load_c_extension(space, filename, modulename):
    from pypy.module.cpyext.api import load_extension_module
    log_pyverbose(space, 1, "import %s # from %s\n" %
                  (modulename, filename))
    load_extension_module(space, filename, modulename)
    # NB. cpyext.api.load_extension_module() can also delegate to _cffi_backend

@jit.dont_look_inside
def load_module(space, w_modulename, find_info, reuse=False):
    """Like load_module() in CPython's import.c, this will normally
    make a module object, store it in sys.modules, execute code in it,
    and then fetch it again from sys.modules.  But this logic is not
    used if we're calling a PEP302 loader.
    """
    if find_info is None:
        return

    if find_info.w_loader:
        return space.call_method(find_info.w_loader, "load_module", w_modulename)

    if find_info.modtype == C_BUILTIN:
        return space.getbuiltinmodule(find_info.filename, force_init=True,
                                      reuse=reuse)

    if find_info.modtype in (PY_SOURCE, PY_COMPILED, C_EXTENSION, PKG_DIRECTORY):
        w_mod = None
        if reuse:
            try:
                w_mod = space.getitem(space.sys.get('modules'), w_modulename)
            except OperationError as oe:
                if not oe.match(space, space.w_KeyError):
                    raise
        if w_mod is None:
            w_mod = Module(space, w_modulename)
        if find_info.modtype == PKG_DIRECTORY:
            pkgdir = find_info.filename
        else:
            pkgdir = None
        _prepare_module(space, w_mod, find_info.filename, pkgdir)

        try:
            if find_info.modtype == PY_SOURCE:
                return load_source_module(
                    space, w_modulename, w_mod,
                    find_info.filename, find_info.stream.readall(),
                    find_info.stream.try_to_find_file_descriptor())
            elif find_info.modtype == PY_COMPILED:
                magic = _r_long(find_info.stream)
                timestamp = _r_long(find_info.stream)
                return load_compiled_module(space, w_modulename, w_mod, find_info.filename,
                                     magic, timestamp, find_info.stream.readall())
            elif find_info.modtype == PKG_DIRECTORY:
                w_path = space.newlist([space.newtext(find_info.filename)])
                space.setattr(w_mod, space.newtext('__path__'), w_path)
                find_info = find_module(space, "__init__", None, "__init__",
                                        w_path, use_loader=False)
                if find_info is None:
                    return w_mod
                try:
                    w_mod = load_module(space, w_modulename, find_info,
                                        reuse=True)
                finally:
                    try:
                        find_info.stream.close()
                    except StreamErrors:
                        pass
                return w_mod
            elif find_info.modtype == C_EXTENSION and has_so_extension(space):
                load_c_extension(space, find_info.filename, space.text_w(w_modulename))
                return check_sys_modules(space, w_modulename)
        except OperationError:
            w_mods = space.sys.get('modules')
            space.call_method(w_mods, 'pop', w_modulename, space.w_None)
            raise

def load_part(space, w_path, prefix, partname, w_parent, tentative):
    modulename = '.'.join(prefix + [partname])
    w_modulename = space.newtext(modulename)
    w_mod = check_sys_modules(space, w_modulename)

    if w_mod is not None:
        if not space.is_w(w_mod, space.w_None):
            return w_mod
    elif not prefix or w_path is not None:
        find_info = find_module(
            space, modulename, w_modulename, partname, w_path)

        try:
            if find_info:
                w_mod = load_module(space, w_modulename, find_info)
                if w_parent is not None:
                    space.setattr(w_parent, space.newtext(partname), w_mod)
                return w_mod
        finally:
            if find_info:
                stream = find_info.stream
                if stream:
                    try:
                        stream.close()
                    except StreamErrors:
                        pass

    if tentative:
        return None
    else:
        # ImportError
        raise oefmt(space.w_ImportError, "No module named %s", modulename)

@jit.dont_look_inside
def reload(space, w_module):
    """Reload the module.
    The module must have been successfully imported before."""
    if not space.is_w(space.type(w_module), space.type(space.sys)):
        raise oefmt(space.w_TypeError, "reload() argument must be module")

    w_modulename = space.getattr(w_module, space.newtext("__name__"))
    modulename = space.text0_w(w_modulename)
    if not space.is_w(check_sys_modules(space, w_modulename), w_module):
        raise oefmt(space.w_ImportError,
                    "reload(): module %s not in sys.modules", modulename)

    try:
        w_mod = space.reloading_modules[modulename]
        # Due to a recursive reload, this module is already being reloaded.
        return w_mod
    except KeyError:
        pass

    space.reloading_modules[modulename] = w_module
    try:
        namepath = modulename.split('.')
        subname = namepath[-1]
        parent_name = '.'.join(namepath[:-1])
        if parent_name:
            w_parent = check_sys_modules_w(space, parent_name)
            if w_parent is None:
                raise oefmt(space.w_ImportError,
                            "reload(): parent %s not in sys.modules",
                            parent_name)
            w_path = space.getattr(w_parent, space.newtext("__path__"))
        else:
            w_path = None

        find_info = find_module(
            space, modulename, w_modulename, subname, w_path)

        if not find_info:
            # ImportError
            raise oefmt(space.w_ImportError, "No module named %s", modulename)

        try:
            try:
                return load_module(space, w_modulename, find_info, reuse=True)
            finally:
                if find_info.stream:
                    find_info.stream.close()
        except:
            # load_module probably removed name from modules because of
            # the error.  Put back the original module object.
            space.sys.setmodule(w_module)
            raise
    finally:
        del space.reloading_modules[modulename]


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

   CPython uses values between 20121 - 62xxx

"""

# picking a magic number is a mess.  So far it works because we
# have only one extra opcode which might or might not be present.
# CPython leaves a gap of 10 when it increases its own magic number.
# To avoid assigning exactly the same numbers as CPython, we can pick
# any number between CPython + 2 and CPython + 9.  Right now,
# default_magic = CPython + 7.
#
#     CPython + 0                  -- used by CPython without the -U option
#     CPython + 1                  -- used by CPython with the -U option
#     CPython + 7 = default_magic  -- used by PyPy (incompatible!)
#
from pypy.interpreter.pycode import default_magic
MARSHAL_VERSION_FOR_PYC = 2

def get_pyc_magic(space):
    # XXX CPython testing hack: delegate to the real imp.get_magic
    if not we_are_translated():
        if '__pypy__' not in space.builtin_modules:
            import struct
            magic = __import__('imp').get_magic()
            return struct.unpack('<i', magic)[0]

    return default_magic


def parse_source_module(space, pathname, source):
    """ Parse a source file and return the corresponding code object """
    ec = space.getexecutioncontext()
    pycode = ec.compiler.compile(source, pathname, 'exec', 0)
    return pycode

def exec_code_module(space, w_mod, code_w, w_modulename, check_afterwards=True):
    """
    Execute a code object in the module's dict.  Returns
    'sys.modules[modulename]', which must exist.
    """
    w_dict = space.getattr(w_mod, space.newtext('__dict__'))
    space.call_method(w_dict, 'setdefault',
                      space.newtext('__builtins__'),
                      space.builtin)
    code_w.exec_code(space, w_dict, w_dict)

    if check_afterwards:
        w_mod = check_sys_modules(space, w_modulename)
        if w_mod is None:
            raise oefmt(space.w_ImportError,
                        "Loaded module %R not found in sys.modules",
                        w_modulename)
    return w_mod


@jit.dont_look_inside
def load_source_module(space, w_modulename, w_mod, pathname, source, fd,
                       write_pyc=True, check_afterwards=True):
    """
    Load a source module from a given file.  Returns the result
    of sys.modules[modulename], which must exist.
    """

    log_pyverbose(space, 1, "import %s # from %s\n" %
                  (space.text_w(w_modulename), pathname))

    src_stat = os.fstat(fd)
    cpathname = pathname + 'c'
    mtime = int(src_stat[stat.ST_MTIME])
    mode = src_stat[stat.ST_MODE]
    stream = check_compiled_module(space, cpathname, mtime)

    if stream:
        # existing and up-to-date .pyc file
        try:
            code_w = read_compiled_module(space, cpathname, stream.readall())
        finally:
            try:
                stream.close()
            except StreamErrors:
                pass
        space.setattr(w_mod, space.newtext('__file__'), space.newtext(cpathname))
    else:
        code_w = parse_source_module(space, pathname, source)

        if write_pyc:
            if not space.is_true(space.sys.get('dont_write_bytecode')):
                write_compiled_module(space, code_w, cpathname, mode, mtime)

    try:
        optimize = space.sys.get_flag('optimize')
    except RuntimeError:
        # during bootstrapping
        optimize = 0
    if optimize >= 2:
        code_w.remove_docstrings(space)

    update_code_filenames(space, code_w, pathname)
    return exec_code_module(space, w_mod, code_w, w_modulename,
                            check_afterwards=check_afterwards)

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

def _read_n(stream, n):
    buf = ''
    while len(buf) < n:
        data = stream.read(n - len(buf))
        if not data:
            raise streamio.StreamError("end of file")
        buf += data
    return buf

def _r_long(stream):
    s = _read_n(stream, 4)
    return _get_long(s)

def _w_long(stream, x):
    a = x & 0xff
    x >>= 8
    b = x & 0xff
    x >>= 8
    c = x & 0xff
    x >>= 8
    d = x & 0xff
    stream.write(chr(a) + chr(b) + chr(c) + chr(d))

def check_compiled_module(space, pycfilename, expected_mtime):
    """
    Check if a pyc file's magic number and mtime match.
    """
    stream = None
    try:
        stream = streamio.open_file_as_stream(pycfilename, "rb")
        magic = _r_long(stream)
        if magic != get_pyc_magic(space):
            stream.close()
            return None
        pyc_mtime = _r_long(stream)
        if pyc_mtime != expected_mtime:
            stream.close()
            return None
        return stream
    except StreamErrors:
        if stream:
            try:
                stream.close()
            except StreamErrors:
                pass
        return None    # XXX! must not eat all exceptions, e.g.
                       # Out of file descriptors.

def read_compiled_module(space, cpathname, strbuf):
    """ Read a code object from a file and check it for validity """

    w_marshal = space.getbuiltinmodule('marshal')
    w_code = space.call_method(w_marshal, 'loads', space.newbytes(strbuf))
    if not isinstance(w_code, Code):
        raise oefmt(space.w_ImportError, "Non-code object in %s", cpathname)
    return w_code

@jit.dont_look_inside
def load_compiled_module(space, w_modulename, w_mod, cpathname, magic,
                         timestamp, source, check_afterwards=True):
    """
    Load a module from a compiled file and execute it.  Returns
    'sys.modules[modulename]', which must exist.
    """
    log_pyverbose(space, 1, "import %s # compiled from %s\n" %
                  (space.text_w(w_modulename), cpathname))

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

    return exec_code_module(space, w_mod, code_w, w_modulename,
                            check_afterwards=check_afterwards)

def open_exclusive(space, cpathname, mode):
    try:
        os.unlink(cpathname)
    except OSError:
        pass

    flags = (os.O_EXCL|os.O_CREAT|os.O_WRONLY|os.O_TRUNC|
             streamio.O_BINARY)
    fd = os.open(cpathname, flags, mode)
    return streamio.fdopen_as_stream(fd, "wb")

def write_compiled_module(space, co, cpathname, src_mode, src_mtime):
    """
    Write a compiled module to a file, placing the time of last
    modification of its source into the header.
    Errors are ignored, if a write error occurs an attempt is made to
    remove the file.
    """
    w_marshal = space.getbuiltinmodule('marshal')
    try:
        w_str = space.call_method(w_marshal, 'dumps', co,
                                  space.newint(MARSHAL_VERSION_FOR_PYC))
        strbuf = space.text_w(w_str)
    except OperationError as e:
        if e.async(space):
            raise
        #print "Problem while marshalling %s, skipping" % cpathname
        return
    #
    # Careful here: we must not crash nor leave behind something that looks
    # too much like a valid pyc file but really isn't one.
    #
    mode = src_mode & ~0111
    try:
        stream = open_exclusive(space, cpathname, mode)
    except (OSError, StreamErrors):
        try:
            os.unlink(cpathname)
        except OSError:
            pass
        return

    try:
        try:
            # will patch the header later; write zeroes until we are sure that
            # the rest of the file is valid
            _w_long(stream, 0)   # pyc_magic
            _w_long(stream, 0)   # mtime
            stream.write(strbuf)

            # should be ok (XXX or should call os.fsync() to be sure?)
            stream.seek(0, 0)
            _w_long(stream, get_pyc_magic(space))
            _w_long(stream, src_mtime)
        finally:
            stream.close()
    except StreamErrors:
        try:
            os.unlink(cpathname)
        except OSError:
            pass
