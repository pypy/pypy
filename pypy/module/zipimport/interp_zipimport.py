
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

zip_importer_cache = {}

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
        self.filelist_w = space.unpackiterable(
            space.getattr(w_dir, space.wrap('filelist')))
        # XXX unicode?
        self.namelist = [space.str_w(i) for i in space.unpackiterable(
            space.call(space.getattr(w_dir, space.wrap('namelist')),
                       space.newlist([])))]

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

    def import_pyc_file(self, space, modname, filename, w_buf, pkgpath):
        w = space.wrap
        buf = space.str_w(w_buf)
        magic = importing._get_long(buf[:4])
        timestamp = importing._get_long(buf[4:8])
        buf = buf[8:] # XXX ugly copy, should use sequential read instead
        w_mod = w(Module(space, w(modname)))
        real_name = self.name + os.path.sep + filename
        importing._prepare_module(space, w_mod, real_name, pkgpath)
        result = importing.load_compiled_module(space, w(modname), w_mod,
                                                filename, magic, timestamp,
                                                buf)
        space.setattr(w_mod, w('__loader__'), space.wrap(self))
        return result

    def get_module(self, space, name):
        w = space.wrap
        try:
            return space.call(space.getattr(self.w_dir, w('getinfo')),
                              space.newlist([w(name)]))
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                # should never happen
                raise e
            return space.w_None

    def find_module(self, space, import_name, w_path=None):
        import_name = import_name.replace('.', os.path.sep)
        for _, _, ext in ENUMERATE_EXTS:
            if space.is_true(self.get_module(space, import_name + ext)):
                return space.wrap(self)
    find_module.unwrap_spec = ['self', ObjSpace, str, W_Root]

    def load_module(self, space, name):
        w = space.wrap
        w_modules = space.sys.get('modules')
        try:
            return space.getitem(w_modules, w(name))
        except OperationError, e:
            pass
        filename = name.replace('.', os.path.sep)
        w_ZipImportError = space.getattr(space.getbuiltinmodule('zipimport'),
                                         w('ZipImportError'))
        last_exc = None
        for compiled, is_package, ext in ENUMERATE_EXTS:
            try:
                w_buf = space.call(space.getattr(self.w_dir, w('read')),
                                   space.newlist([w(filename + ext)]))
                if is_package:
                    pkgpath = self.name
                else:
                    pkgpath = None
                if compiled:
                    return self.import_pyc_file(space, name, filename + ext,
                                                w_buf, pkgpath)
                else:
                    return self.import_py_file(space, name, filename + ext,
                                               w_buf, pkgpath)
            except OperationError, e:
                last_exc = e
                w_mods = space.sys.get('modules')
                space.call_method(w_mods,'pop', w(name), space.w_None)
        if last_exc:
            raise OperationError(w_ZipImportError, last_exc.w_value)
        # should never happen I think
        return space.w_None
    load_module.unwrap_spec = ['self', ObjSpace, str]

    def get_data(self, space):
        pass
    get_data.unwrap_spec = ['self', ObjSpace]

    def get_code(self, space):
        pass
    get_code.unwrap_spec = ['self', ObjSpace]

    def get_source(self, space):
        pass
    get_source.unwrap_spec = ['self', ObjSpace]

    def is_package(self, space):
        pass
    is_package.unwrap_spec = ['self', ObjSpace]

def descr_new_zipimporter(space, w_type, name):
    try:
        return zip_importer_cache[name]
    except KeyError:
        pass
    try:
        s = os.stat(name)
    except OSError:
        return space.w_None
    if stat.S_ISDIR(s.st_mode):
        return space.w_None
    w_import = space.builtin.get('__import__')
    w_zipfile = space.call(w_import, space.newlist([
        space.wrap('zipfile'),
        space.newdict(),
        space.newdict(),
        space.newlist([])]))
    w_ZipFile = space.getattr(w_zipfile, space.wrap('ZipFile'))
    try:
        w_dir = space.call(w_ZipFile, space.newlist([space.wrap(name)]))
    except OperationError: # we catch everything as this function
        # should not raise
        return space.w_None
    result = space.wrap(W_ZipImporter(space, name, w_dir, w_zipfile))
    zip_importer_cache[name] = result
    return result
    
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
)
