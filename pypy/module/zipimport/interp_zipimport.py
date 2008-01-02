
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import app2interp
from pypy.interpreter.eval import Code
from pypy.interpreter.module import Module
from pypy.module.__builtin__ import importing
from pypy.rlib.unroll import unrolling_iterable
import os
import stat

ZIPSEP = '/'
# note that zipfiles always use slash, but for OSes with other
# separators, we need to pretend that we had the os.sep.

ENUMERATE_EXTS = unrolling_iterable(
    [(True, True, os.path.sep + '__init__.pyc'),
     (True, True, os.path.sep + '__init__.pyo'),
     (False, True, os.path.sep + '__init__.py'),
     (True, False, '.pyc'),
     (True, False, '.pyo'),
     (False, False, '.py')])

class W_ZipImporter(Wrappable):
    def __init__(self, space, name, w_dir, w_zipfile):
        self.space = space
        self.name = name
        self.w_dir = w_dir
        self.w_zipfile = w_zipfile

    def import_py_file(self, space, modname, filename, w_buf, pkgpath):
        buf = space.str_w(w_buf)
        w = space.wrap
        w_mod = w(Module(space, w(modname)))
        real_name = self.name + os.path.sep + filename
        importing._prepare_module(space, w_mod, real_name, pkgpath)
        result = importing.load_source_module(space, w(modname), w_mod,
                                            filename, buf, write_pyc=False)
        space.setattr(w_mod, w('__loader__'), space.wrap(self))
        return result

    def check_newer_pyfile(self, space, filename, timestamp):
        w = space.wrap
        try:
            w_info = space.call_function(space.getattr(self.w_dir,
                                         w('getinfo')), w(filename))
            w_all = space.getattr(w_info, w('date_time'))
        except OperationError, e:
            # in either case, this is a fallback
            return False
        else:
            w_mktime = space.getattr(space.getbuiltinmodule('time'),
                                     w('mktime'))
            # XXX this is incredible fishing around module limitations
            #     in order to compare timestamps of .py and .pyc files
            all = space.unpackiterable(w_all)
            all += [w(0), w(1), w(-1)]
            mtime = int(space.float_w(space.call_function(w_mktime, space.newtuple(all))))
            return mtime > timestamp

    def import_pyc_file(self, space, modname, filename, w_buf, pkgpath):
        w = space.wrap
        buf = space.str_w(w_buf)
        magic = importing._get_long(buf[:4])
        timestamp = importing._get_long(buf[4:8])
        if self.check_newer_pyfile(space, filename[:-1], timestamp):
            return self.import_py_file(space, modname, filename[:-1], w_buf,
                                       pkgpath)
        buf = buf[8:] # XXX ugly copy, should use sequential read instead
        w_mod = w(Module(space, w(modname)))
        real_name = self.name + os.path.sep + filename
        importing._prepare_module(space, w_mod, real_name, pkgpath)
        result = importing.load_compiled_module(space, w(modname), w_mod,
                                                filename, magic, timestamp,
                                                buf)
        space.setattr(w_mod, w('__loader__'), space.wrap(self))
        return result

    def have_modulefile(self, space, filename):
        if ZIPSEP != os.path.sep:
            filename = filename.replace(os.path.sep, ZIPSEP)
        w = space.wrap
        try:
            return space.call(space.getattr(self.w_dir, w('getinfo')),
                              space.newlist([w(filename)]))
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                # should never happen
                raise e

    def find_module(self, space, fullname, w_path=None):
        filename = self.mangle(fullname)
        for _, _, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                return space.wrap(self)
    find_module.unwrap_spec = ['self', ObjSpace, str, W_Root]

    def mangle(self, name):
        return name.replace('.', os.path.sep)

    def load_module(self, space, fullname):
        w = space.wrap
        w_modules = space.sys.get('modules')
        try:
            return space.getitem(w_modules, w(fullname))
        except OperationError, e:
            pass
        filename = self.mangle(fullname)
        w_ZipImportError = space.getattr(space.getbuiltinmodule('zipimport'),
                                         w('ZipImportError'))
        last_exc = None
        for compiled, is_package, ext in ENUMERATE_EXTS:
            try:
                fname = filename + ext
                w_buf = self.get_data(space, fname)
                if is_package:
                    pkgpath = self.name
                else:
                    pkgpath = None
                if compiled:
                    return self.import_pyc_file(space, fullname, fname,
                                                  w_buf, pkgpath)
                else:
                    return self.import_py_file(space, fullname, fname,
                                               w_buf, pkgpath)
            except OperationError, e:
                last_exc = e
                w_mods = space.sys.get('modules')
                space.call_method(w_mods, 'pop', w(fullname), space.w_None)
        if last_exc:
            raise OperationError(space.w_ImportError, last_exc.w_value)
        # should never happen I think
        return space.w_None
    load_module.unwrap_spec = ['self', ObjSpace, str]

    def get_data(self, space, filename):
        if ZIPSEP != os.path.sep:
            filename = filename.replace(os.path.sep, ZIPSEP)
        w = space.wrap
        try:
            return space.call_function(space.getattr(self.w_dir, w('read')),
                                       w(filename))
        except OperationError, e:
            raise OperationError(space.w_IOError, e.w_value)
    get_data.unwrap_spec = ['self', ObjSpace, str]

    def get_code(self, space, fullname):
        filename = self.mangle(fullname)
        w = space.wrap
        for compiled, _, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                if compiled:
                    return self.get_data(space, filename + ext)
                else:
                    w_source = self.get_data(space, filename + ext)
                    w_code = space.builtin.call('compile', w_source,
                                                w(filename + ext), w('exec'))
                    return w_code 
        raise OperationError(space.w_ImportError, space.wrap(
            "Cannot find source or code for %s in %s" % (filename, self.name)))
    get_code.unwrap_spec = ['self', ObjSpace, str]

    def get_source(self, space, fullname):
        filename = self.mangle(fullname)
        for compiled, _, ext in ENUMERATE_EXTS:
            if not compiled:
                fname = filename + ext
                if self.have_modulefile(space, fname):
                    return self.get_data(space, fname)
        raise OperationError(space.w_ImportError, space.wrap(
            "Cannot find source for %s in %s" % (filename, self.name)))
    get_source.unwrap_spec = ['self', ObjSpace, str]

    def is_package(self, space, fullname):
        filename = self.mangle(fullname)
        for _, is_package, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                return space.wrap(is_package)
        raise OperationError(space.w_ImportError, space.wrap(
            "Cannot find module %s in %s" % (filename, self.name)))
    is_package.unwrap_spec = ['self', ObjSpace, str]

    def getarchive(space, self):
        space = self.space
        return space.getattr(self.w_dir, space.wrap('filename'))


def descr_new_zipimporter(space, w_type, name):
    w_zip_cache = space.getattr(space.getbuiltinmodule('zipimport'),
                                space.wrap('_zip_directory_cache'))
    try:
        w_result = space.getitem(w_zip_cache, space.wrap(name))
        if space.is_w(w_result, space.w_None):
            raise OperationError(space.w_ImportError, space.wrap(
                "Cannot import %s from zipfile, recursion detected or"
                "already tried and failed" % (name,)))
        return w_result
    except OperationError, o:
        if not o.match(space, space.w_KeyError):
            raise
        space.setitem(w_zip_cache, space.wrap(name), space.w_None)
    ok = False
    parts = name.split(os.path.sep)
    filename = "" # make annotator happy
    for i in range(1, len(parts) + 1):
        filename = os.path.sep.join(parts[:i])
        if not filename:
            filename = os.path.sep
        try:
            s = os.stat(filename)
        except OSError:
            raise OperationError(space.w_ImportError, space.wrap(
                "Cannot find name %s" % (filename,)))
        if not stat.S_ISDIR(s.st_mode):
            ok = True
            break
    if not ok:
        raise OperationError(space.w_ImportError, space.wrap(
            "Did not find %s to be a valid zippath" % (name,)))
    w_import = space.builtin.get('__import__')
    w_zipfile = space.call(w_import, space.newlist([
        space.wrap('zipfile'),
        space.newdict(),
        space.newdict(),
        space.newlist([])]))
    w_ZipFile = space.getattr(w_zipfile, space.wrap('ZipFile'))
    try:
        w_dir = space.call(w_ZipFile, space.newlist([space.wrap(filename)]))
    except OperationError, e: # we catch everything as this function
        raise OperationError(space.w_ImportError, space.wrap(
            "%s seems not to be a zipfile" % (filename,)))
    w_result = space.wrap(W_ZipImporter(space, name, w_dir, w_zipfile))
    space.setitem(w_zip_cache, space.wrap(name), w_result)
    return w_result
    
descr_new_zipimporter.unwrap_spec = [ObjSpace, W_Root, str]

W_ZipImporter.typedef = TypeDef(
    'zipimporter',
    __new__     = interp2app(descr_new_zipimporter),
    find_module = interp2app(W_ZipImporter.find_module),
    get_data    = interp2app(W_ZipImporter.get_data),
    get_code    = interp2app(W_ZipImporter.get_code),
    get_source  = interp2app(W_ZipImporter.get_source),
    is_package  = interp2app(W_ZipImporter.is_package),
    load_module = interp2app(W_ZipImporter.load_module),
    archive     = GetSetProperty(W_ZipImporter.getarchive),
)
