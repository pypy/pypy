"""
Implementation of the interpreter-level default import logic.
"""

import sys, os, stat

from pypy.interpreter.module import Module
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, generic_new_descr
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.eval import Code
from pypy.interpreter.pycode import PyCode
from pypy.rlib import streamio, jit
from pypy.rlib.streamio import StreamErrors
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.module.sys.version import PYPY_VERSION

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

if sys.platform == 'win32':
    SO = ".pyd"
else:
    SO = ".so"
DEFAULT_SOABI = 'pypy-%d%d' % PYPY_VERSION[:2]
CHECK_FOR_PYW = sys.platform == 'win32'

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

def find_modtype(space, filepart):
    """Check which kind of module to import for the given filepart,
    which is a path without extension.  Returns PY_SOURCE, PY_COMPILED or
    SEARCH_ERROR.
    """
    # check the .py file
    pyfile = filepart + ".py"
    if os.path.exists(pyfile) and case_ok(pyfile):
        return PY_SOURCE, ".py", "U"

    # on Windows, also check for a .pyw file
    if CHECK_FOR_PYW:
        pyfile = filepart + ".pyw"
        if os.path.exists(pyfile) and case_ok(pyfile):
            return PY_SOURCE, ".pyw", "U"

    # The .py file does not exist.  By default on PyPy, lonepycfiles
    # is False: if a .py file does not exist, we don't even try to
    # look for a lone .pyc file.
    # The "imp" module does not respect this, and is allowed to find
    # lone .pyc files.
    # check the .pyc file
    if space.config.objspace.usepycfiles and space.config.objspace.lonepycfiles:
        pycfile = filepart + ".pyc"
        if os.path.exists(pycfile) and case_ok(pycfile):
            # existing .pyc file
            return PY_COMPILED, ".pyc", "rb"

    if space.config.objspace.usemodules.cpyext:
        so_extension = get_so_extension(space)
        pydfile = filepart + so_extension
        if os.path.exists(pydfile) and case_ok(pydfile):
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
    except OperationError, e:
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
    w = space.wrap
    ctxt_w_package = space.finditem_str(w_globals, '__package__')
    ctxt_w_package = jit.promote(ctxt_w_package)
    level = jit.promote(level)

    ctxt_package = None
    if ctxt_w_package is not None and ctxt_w_package is not space.w_None:
        try:
            ctxt_package = space.str_w(ctxt_w_package)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            raise OperationError(space.w_ValueError, space.wrap(
                "__package__ set to non-string"))

    if ctxt_package is not None:
        # __package__ is set, so use it
        if ctxt_package == '' and level < 0:
            return None, 0

        dot_position = _get_dot_position(ctxt_package, level - 1)
        if dot_position < 0:
            if len(ctxt_package) == 0:
                msg = "Attempted relative import in non-package"
            else:
                msg = "Attempted relative import beyond toplevel package"
            raise OperationError(space.w_ValueError, w(msg))

        # Try to import parent package
        try:
            w_parent = absolute_import(space, ctxt_package, 0,
                                       None, tentative=False)
        except OperationError, e:
            if not e.match(space, space.w_ImportError):
                raise
            if level > 0:
                raise OperationError(space.w_SystemError, space.wrap(
                    "Parent module '%s' not loaded, "
                    "cannot perform relative import" % ctxt_package))
            else:
                space.warn("Parent module '%s' not found "
                           "while handling absolute import" % ctxt_package,
                           space.w_RuntimeWarning)

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
                ctxt_name = space.str_w(ctxt_w_name)
            except OperationError, e:
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
                msg = "Attempted relative import in non-package"
                raise OperationError(space.w_ValueError, w(msg))
            rel_modulename = ''
            rel_level = 0
        else:
            rel_modulename = ctxt_name[:dot_position]
            rel_level = rel_modulename.count('.') + 1

        if ctxt_w_path is not None:
            # __path__ is set, so __name__ is already the package name
            space.setitem(w_globals, w("__package__"), ctxt_w_name)
        else:
            # Normal module, so work out the package name if any
            last_dot_position = ctxt_name.rfind('.')
            if last_dot_position < 0:
                space.setitem(w_globals, w("__package__"), space.w_None)
            else:
                space.setitem(w_globals, w("__package__"),
                              w(ctxt_name[:last_dot_position]))

        if modulename:
            if rel_modulename:
                rel_modulename += '.' + modulename
            else:
                rel_modulename = modulename

    return rel_modulename, rel_level


@unwrap_spec(name=str, level=int)
def importhook(space, name, w_globals=None,
               w_locals=None, w_fromlist=None, level=-1):
    modulename = name
    space.timer.start_name("importhook", modulename)
    if not modulename and level < 0:
        raise OperationError(
            space.w_ValueError,
            space.wrap("Empty module name"))
    w = space.wrap

    if w_fromlist is not None and space.is_true(w_fromlist):
        fromlist_w = space.fixedview(w_fromlist)
    else:
        fromlist_w = None

    rel_modulename = None
    if (level != 0 and
        w_globals is not None and
        space.isinstance_w(w_globals, space.w_dict)):

        rel_modulename, rel_level = _get_relative_name(space, modulename, level, w_globals)

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
                    # already tried and failed and falled back to the
                    # end of this function.
                    w_mod = None
                else:
                    w_mod = absolute_import(space, rel_modulename, rel_level,
                                            fromlist_w, tentative=True)
            else:
                w_mod = absolute_import(space, rel_modulename, rel_level,
                                        fromlist_w, tentative=False)
            if w_mod is not None:
                space.timer.stop_name("importhook", modulename)
                return w_mod

    w_mod = absolute_import(space, modulename, 0, fromlist_w, tentative=0)
    if rel_modulename is not None:
        space.setitem(space.sys.get('modules'), w(rel_modulename), space.w_None)
    space.timer.stop_name("importhook", modulename)
    return w_mod

def absolute_import(space, modulename, baselevel, fromlist_w, tentative):
    # Short path: check in sys.modules
    w_mod = absolute_import_try(space, modulename, baselevel, fromlist_w)
    if w_mod is not None and not space.is_w(w_mod, space.w_None):
        return w_mod
    return absolute_import_with_lock(space, modulename, baselevel,
                                     fromlist_w, tentative)

@jit.dont_look_inside
def absolute_import_with_lock(space, modulename, baselevel,
                              fromlist_w, tentative):
    lock = getimportlock(space)
    lock.acquire_lock()
    try:
        return _absolute_import(space, modulename, baselevel,
                                fromlist_w, tentative)
    finally:
        lock.release_lock()

@jit.unroll_safe
def absolute_import_try(space, modulename, baselevel, fromlist_w):
    """ Only look up sys.modules, not actually try to load anything
    """
    w_path = None
    last_dot = 0
    if '.' not in modulename:
        w_mod = check_sys_modules_w(space, modulename)
        first = w_mod
        if fromlist_w is not None and w_mod is not None:
            w_path = try_getattr(space, w_mod, space.wrap('__path__'))
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
            if fromlist_w is not None:
                w_path = try_getattr(space, w_mod, space.wrap('__path__'))
            level += 1
    if fromlist_w is not None:
        if w_path is not None:
            if len(fromlist_w) == 1 and space.eq_w(fromlist_w[0],
                                                   space.wrap('*')):
                w_all = try_getattr(space, w_mod, space.wrap('__all__'))
                if w_all is not None:
                    fromlist_w = space.fixedview(w_all)
            for w_name in fromlist_w:
                if try_getattr(space, w_mod, w_name) is None:
                    return None
        return w_mod
    return first

def _absolute_import(space, modulename, baselevel, fromlist_w, tentative):
    w = space.wrap

    if '/' in modulename or '\\' in modulename:
        raise OperationError(space.w_ImportError, space.wrap(
            "Import by filename is not supported."))

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
        w_path = try_getattr(space, w_mod, w('__path__'))
        level += 1

    if fromlist_w is not None:
        if w_path is not None:
            if len(fromlist_w) == 1 and space.eq_w(fromlist_w[0],w('*')):
                w_all = try_getattr(space, w_mod, w('__all__'))
                if w_all is not None:
                    fromlist_w = space.fixedview(w_all)
            for w_name in fromlist_w:
                if try_getattr(space, w_mod, w_name) is None:
                    load_part(space, w_path, prefix, space.str_w(w_name), w_mod,
                              tentative=1)
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
            except OperationError, e:
                if not e.match(space, space.w_ImportError):
                    raise
            else:
                break
        if w_importer is None:
            try:
                w_importer = space.call_function(
                    space.gettypefor(W_NullImporter), w_pathitem
                )
            except OperationError, e:
                if e.match(space, space.w_ImportError):
                    return None
                raise
        if space.is_true(w_importer):
            space.setitem(w_path_importer_cache, w_pathitem, w_importer)
    return w_importer

def find_in_path_hooks(space, w_modulename, w_pathitem):
    w_importer = _getimporter(space, w_pathitem)
    if w_importer is not None and space.is_true(w_importer):
        w_loader = space.call_method(w_importer, "find_module", w_modulename)
        if space.is_true(w_loader):
            return w_loader


class W_NullImporter(Wrappable):
    def __init__(self, space):
        pass

    @unwrap_spec(path=str)
    def descr_init(self, space, path):
        if not path:
            raise OperationError(space.w_ImportError, space.wrap(
                "empty pathname"))

        # Directory should not exist
        try:
            st = os.stat(path)
        except OSError:
            pass
        else:
            if stat.S_ISDIR(st.st_mode):
                raise OperationError(space.w_ImportError, space.wrap(
                    "existing directory"))

    def find_module_w(self, space, __args__):
        return space.wrap(None)

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

    if w_path is None:
        # check the builtin modules
        if modulename in space.builtin_modules:
            return FindInfo(C_BUILTIN, modulename, None)
        w_path = space.sys.get('path')

    # XXX check frozen modules?
    #     when w_path is null

    if w_path is not None:
        for w_pathitem in space.unpackiterable(w_path):
            # sys.path_hooks import hook
            if use_loader:
                w_loader = find_in_path_hooks(space, w_modulename, w_pathitem)
                if w_loader:
                    return FindInfo.fromLoader(w_loader)

            path = space.str_w(w_pathitem)
            filepart = os.path.join(path, partname)
            if os.path.isdir(filepart) and case_ok(filepart):
                initfile = os.path.join(filepart, '__init__')
                modtype, _, _ = find_modtype(space, initfile)
                if modtype in (PY_SOURCE, PY_COMPILED):
                    return FindInfo(PKG_DIRECTORY, filepart, None)
                else:
                    msg = "Not importing directory " +\
                            "'%s' missing __init__.py" % (filepart,)
                    space.warn(msg, space.w_ImportWarning)
            modtype, suffix, filemode = find_modtype(space, filepart)
            try:
                if modtype in (PY_SOURCE, PY_COMPILED):
                    assert suffix is not None
                    filename = filepart + suffix
                    stream = streamio.open_file_as_stream(filename, filemode)
                    try:
                        return FindInfo(modtype, filename, stream, suffix, filemode)
                    except:
                        stream.close()
                        raise
                if modtype == C_EXTENSION:
                    filename = filepart + suffix
                    return FindInfo(modtype, filename, None, suffix, filemode)
            except StreamErrors:
                pass   # XXX! must not eat all exceptions, e.g.
                       # Out of file descriptors.

    # not found
    return None

def _prepare_module(space, w_mod, filename, pkgdir):
    w = space.wrap
    space.sys.setmodule(w_mod)
    space.setattr(w_mod, w('__file__'), space.wrap(filename))
    space.setattr(w_mod, w('__doc__'), space.w_None)
    if pkgdir is not None:
        space.setattr(w_mod, w('__path__'), space.newlist([w(pkgdir)]))

def load_c_extension(space, filename, modulename):
    # the next line is mandatory to init cpyext
    space.getbuiltinmodule("cpyext")
    from pypy.module.cpyext.api import load_extension_module
    load_extension_module(space, filename, modulename)

@jit.dont_look_inside
def load_module(space, w_modulename, find_info, reuse=False):
    if find_info is None:
        return
    if find_info.w_loader:
        return space.call_method(find_info.w_loader, "load_module", w_modulename)

    if find_info.modtype == C_BUILTIN:
        return space.getbuiltinmodule(find_info.filename, force_init=True)

    if find_info.modtype in (PY_SOURCE, PY_COMPILED, C_EXTENSION, PKG_DIRECTORY):
        w_mod = None
        if reuse:
            try:
                w_mod = space.getitem(space.sys.get('modules'), w_modulename)
            except OperationError, oe:
                if not oe.match(space, space.w_KeyError):
                    raise
        if w_mod is None:
            w_mod = space.wrap(Module(space, w_modulename))
        if find_info.modtype == PKG_DIRECTORY:
            pkgdir = find_info.filename
        else:
            pkgdir = None
        _prepare_module(space, w_mod, find_info.filename, pkgdir)

        try:
            if find_info.modtype == PY_SOURCE:
                load_source_module(space, w_modulename, w_mod, find_info.filename,
                                   find_info.stream.readall())
                return w_mod
            elif find_info.modtype == PY_COMPILED:
                magic = _r_long(find_info.stream)
                timestamp = _r_long(find_info.stream)
                load_compiled_module(space, w_modulename, w_mod, find_info.filename,
                                     magic, timestamp, find_info.stream.readall())
                return w_mod
            elif find_info.modtype == PKG_DIRECTORY:
                w_path = space.newlist([space.wrap(find_info.filename)])
                space.setattr(w_mod, space.wrap('__path__'), w_path)
                find_info = find_module(space, "__init__", None, "__init__",
                                        w_path, use_loader=False)
                if find_info is None:
                    return w_mod
                try:
                    load_module(space, w_modulename, find_info, reuse=True)
                finally:
                    find_info.stream.close()
                # fetch the module again, in case of "substitution"
                w_mod = check_sys_modules(space, w_modulename)
                return w_mod
            elif find_info.modtype == C_EXTENSION and space.config.objspace.usemodules.cpyext:
                load_c_extension(space, find_info.filename, space.str_w(w_modulename))
                return check_sys_modules(space, w_modulename)
        except OperationError:
            w_mods = space.sys.get('modules')
            space.call_method(w_mods, 'pop', w_modulename, space.w_None)
            raise

def load_part(space, w_path, prefix, partname, w_parent, tentative):
    w = space.wrap
    modulename = '.'.join(prefix + [partname])
    w_modulename = w(modulename)
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
                try:
                    w_mod = space.getitem(space.sys.get("modules"),
                                          w_modulename)
                except OperationError, oe:
                    if not oe.match(space, space.w_KeyError):
                        raise
                    raise OperationError(space.w_ImportError, w_modulename)
                if w_parent is not None:
                    space.setattr(w_parent, space.wrap(partname), w_mod)
                return w_mod
        finally:
            if find_info:
                stream = find_info.stream
                if stream:
                    stream.close()

    if tentative:
        return None
    else:
        # ImportError
        msg = "No module named %s"
        raise operationerrfmt(space.w_ImportError, msg, modulename)

@jit.dont_look_inside
def reload(space, w_module):
    """Reload the module.
    The module must have been successfully imported before."""
    if not space.is_w(space.type(w_module), space.type(space.sys)):
        raise OperationError(
            space.w_TypeError,
            space.wrap("reload() argument must be module"))

    w_modulename = space.getattr(w_module, space.wrap("__name__"))
    modulename = space.str_w(w_modulename)
    if not space.is_w(check_sys_modules(space, w_modulename), w_module):
        raise operationerrfmt(
            space.w_ImportError,
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
        parent = None
        if parent_name:
            w_parent = check_sys_modules_w(space, parent_name)
            if w_parent is None:
                raise operationerrfmt(
                    space.w_ImportError,
                    "reload(): parent %s not in sys.modules",
                    parent_name)
            w_path = space.getattr(w_parent, space.wrap("__path__"))
        else:
            w_path = None

        find_info = find_module(
            space, modulename, w_modulename, subname, w_path)

        if not find_info:
            # ImportError
            msg = "No module named %s"
            raise operationerrfmt(space.w_ImportError, msg, modulename)

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

    def lock_held(self):
        me = self.space.getexecutioncontext()   # used as thread ident
        return self.lockowner is me

    def _can_have_lock(self):
        # hack: we can't have self.lock != None during translation,
        # because prebuilt lock objects are not allowed.  In this
        # special situation we just don't lock at all (translation is
        # not multithreaded anyway).
        if we_are_translated():
            return True     # we need a lock at run-time
        elif self.space.config.translating:
            assert self.lock is None
            return False
        else:
            return True     # in py.py

    def acquire_lock(self):
        # this function runs with the GIL acquired so there is no race
        # condition in the creation of the lock
        if self.lock is None:
            if not self._can_have_lock():
                return
            self.lock = self.space.allocate_lock()
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.lockowner is me:
            pass    # already acquired by the current thread
        else:
            self.lock.acquire(True)
            assert self.lockowner is None
            assert self.lockcounter == 0
            self.lockowner = me
        self.lockcounter += 1

    def release_lock(self):
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.lockowner is not me:
            if not self._can_have_lock():
                return
            space = self.space
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("not holding the import lock"))
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
# have only one extra opcode, which bumps the magic number by +2, and CPython
# leaves a gap of 10 when it increases
# its own magic number.  To avoid assigning exactly the same numbers
# as CPython we always add a +2.  We'll have to think again when we
# get three more new opcodes
#
#  * CALL_METHOD            +2
#
# In other words:
#
#     default_magic        -- used by CPython without the -U option
#     default_magic + 1    -- used by CPython with the -U option
#     default_magic + 2    -- used by PyPy without any extra opcode
#     ...
#     default_magic + 5    -- used by PyPy with both extra opcodes
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

    result = default_magic
    if space.config.objspace.opcodes.CALL_METHOD:
        result += 2
    return result


def parse_source_module(space, pathname, source):
    """ Parse a source file and return the corresponding code object """
    ec = space.getexecutioncontext()
    pycode = ec.compiler.compile(source, pathname, 'exec', 0)
    return pycode

def exec_code_module(space, w_mod, code_w):
    w_dict = space.getattr(w_mod, space.wrap('__dict__'))
    space.call_method(w_dict, 'setdefault',
                      space.wrap('__builtins__'),
                      space.wrap(space.builtin))
    code_w.exec_code(space, w_dict, w_dict)


@jit.dont_look_inside
def load_source_module(space, w_modulename, w_mod, pathname, source,
                       write_pyc=True):
    """
    Load a source module from a given file and return its module
    object.
    """
    w = space.wrap

    if space.config.objspace.usepycfiles:
        cpathname = pathname + 'c'
        src_stat = os.stat(pathname)
        mtime = int(src_stat[stat.ST_MTIME])
        mode = src_stat[stat.ST_MODE]
        stream = check_compiled_module(space, cpathname, mtime)
    else:
        cpathname = None
        mtime = 0
        mode = 0
        stream = None

    if stream:
        # existing and up-to-date .pyc file
        try:
            code_w = read_compiled_module(space, cpathname, stream.readall())
        finally:
            stream.close()
        space.setattr(w_mod, w('__file__'), w(cpathname))
    else:
        code_w = parse_source_module(space, pathname, source)

        if space.config.objspace.usepycfiles and write_pyc:
            if not space.is_true(space.sys.get('dont_write_bytecode')):
                write_compiled_module(space, code_w, cpathname, mode, mtime)

    update_code_filenames(space, code_w, pathname)
    exec_code_module(space, w_mod, code_w)

    return w_mod

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
            stream.close()
        return None    # XXX! must not eat all exceptions, e.g.
                       # Out of file descriptors.

def read_compiled_module(space, cpathname, strbuf):
    """ Read a code object from a file and check it for validity """

    w_marshal = space.getbuiltinmodule('marshal')
    w_code = space.call_method(w_marshal, 'loads', space.wrap(strbuf))
    pycode = space.interpclass_w(w_code)
    if pycode is None or not isinstance(pycode, Code):
        raise operationerrfmt(space.w_ImportError,
                              "Non-code object in %s", cpathname)
    return pycode

@jit.dont_look_inside
def load_compiled_module(space, w_modulename, w_mod, cpathname, magic,
                         timestamp, source):
    """
    Load a module from a compiled file, execute it, and return its
    module object.
    """
    w = space.wrap
    if magic != get_pyc_magic(space):
        raise operationerrfmt(space.w_ImportError,
                              "Bad magic number in %s", cpathname)
    #print "loading pyc file:", cpathname
    code_w = read_compiled_module(space, cpathname, source)
    exec_code_module(space, w_mod, code_w)

    return w_mod

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
        w_str = space.call_method(w_marshal, 'dumps', space.wrap(co),
                                  space.wrap(MARSHAL_VERSION_FOR_PYC))
        strbuf = space.str_w(w_str)
    except OperationError, e:
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
