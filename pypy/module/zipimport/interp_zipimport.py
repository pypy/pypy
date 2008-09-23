
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.module import Module
from pypy.module.__builtin__ import importing
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rzipfile import RZipFile, BadZipfile
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

class W_ZipCache(Wrappable):
    def __init__(self):
        self.cache = {}

    def get(self, name):
        return self.cache[name]

    def set(self, name, w_importer):
        self.cache[name] = w_importer

    # -------------- dict-like interface -----------------
    # I don't care about speed of those, they're obscure anyway
    # THIS IS A TERRIBLE HACK TO BE CPYTHON COMPATIBLE
        
    def getitem(self, space, name):
        try:
            w_zipimporter = self.cache[name]
        except KeyError:
            raise OperationError(space.w_KeyError, space.wrap(name))
        assert isinstance(w_zipimporter, W_ZipImporter)
        dir = w_zipimporter.dir
        keys = [k.filename for k in dir.filelist]
        w = space.wrap
        values = {}
        w_d = space.newdict()
        for key in keys:
            info = dir.NameToInfo[key]
            w_values = space.newdict()
            space.setitem(w_d, w(key), space.newtuple([
                w(info.filename), w(info.compress_type), w(info.compress_size),
                w(info.file_size), w(info.file_offset), w(info.dostime),
                w(info.dosdate), w(info.CRC)]))
        return w_d
    getitem.unwrap_spec = ['self', ObjSpace, str]

    def keys(self, space):
        return space.newlist([space.wrap(s)
                              for s in self.cache.keys()])
    keys.unwrap_spec = ['self', ObjSpace]

    def values(self, space):
        keys = self.cache.keys()
        values_w = [self.getitem(space, key) for key in keys]
        return space.newlist(values_w)
    values.unwrap_spec = ['self', ObjSpace]

    def items(self, space):
        w = space.wrap
        items_w = [space.newtuple([w(key), self.getitem(space, key)])
                   for key in self.cache.keys()]
        return space.newlist(items_w)
    items.unwrap_spec = ['self', ObjSpace]

    def iterkeys(self, space):
        return space.iter(self.keys(space))
    iterkeys.unwrap_spec = ['self', ObjSpace]

    def itervalues(self, space):
        return space.iter(self.values(space))
    itervalues.unwrap_spec = ['self', ObjSpace]

    def iteritems(self, space):
        return space.iter(self.items(space))
    iteritems.unwrap_spec = ['self', ObjSpace]

    def contains(self, space, name):
        return space.newbool(name in self.cache)
    contains.unwrap_spec = ['self', ObjSpace, str]

    def clear(self, space):
        self.cache = {}
    clear.unwrap_spec = ['self', ObjSpace]

    def delitem(self, space, name):
        del self.cache[name]
    delitem.unwrap_spec = ['self', ObjSpace, str]

W_ZipCache.typedef = TypeDef(
    'zip_dict',
    __getitem__ = interp2app(W_ZipCache.getitem),
    __contains__ = interp2app(W_ZipCache.contains),
    __iter__ = interp2app(W_ZipCache.iterkeys),
    items = interp2app(W_ZipCache.items),
    iteritems = interp2app(W_ZipCache.iteritems),
    keys = interp2app(W_ZipCache.keys),
    iterkeys = interp2app(W_ZipCache.iterkeys),
    values = interp2app(W_ZipCache.values),
    itervalues = interp2app(W_ZipCache.itervalues),
    clear = interp2app(W_ZipCache.clear),
    __delitem__ = interp2app(W_ZipCache.delitem),
)

zip_cache = W_ZipCache()

class W_ZipImporter(Wrappable):
    def __init__(self, space, name, dir, prefix):
        self.space = space
        self.name = name
        self.dir = dir
        self.prefix = prefix
        self.w_ZipImportError = space.getattr(
            space.getbuiltinmodule('zipimport'),
            space.wrap('ZipImportError'))

    def getprefix(space, self):
        return space.wrap(self.prefix)

    def _find_relative_path(self, filename):
        if filename.startswith(self.dir.filename):
            filename = filename[len(self.dir.filename):]
        if filename.startswith(os.sep):
            filename = filename[1:]
        if ZIPSEP != os.path.sep:
            filename = filename.replace(os.path.sep, ZIPSEP)
        return filename

    def import_py_file(self, space, modname, filename, buf, pkgpath):
        w = space.wrap
        w_mod = w(Module(space, w(modname)))
        real_name = self.name + os.path.sep + filename
        space.setattr(w_mod, w('__loader__'), space.wrap(self))
        importing._prepare_module(space, w_mod, real_name, pkgpath)
        result = importing.load_source_module(space, w(modname), w_mod,
                                            filename, buf, write_pyc=False)
        return result

    def _parse_mtime(self, space, filename):
        w = space.wrap
        try:
            info = self.dir.getinfo(filename)
            t = info.date_time
        except (BadZipfile, KeyError):
            # in either case, this is a fallback
            return 0
        else:
            w_mktime = space.getattr(space.getbuiltinmodule('time'),
                                     w('mktime'))
            # XXX this is incredible fishing around module limitations
            #     in order to compare timestamps of .py and .pyc files
            # we need time.mktime support on rpython level
            all = [w(t[0]), w(t[1]), w(t[2]), w(t[3]), w(t[4]),
                   w(t[5]), w(0), w(1), w(-1)]
            mtime = int(space.float_w(space.call_function(w_mktime, space.newtuple(all))))
            return mtime

    def check_newer_pyfile(self, space, filename, timestamp):
        mtime = self._parse_mtime(space, filename)
        if mtime == 0:
            return False
        return mtime > timestamp

    def check_compatible_mtime(self, space, filename, timestamp):
        mtime = self._parse_mtime(space, filename)
        if mtime == 0 or mtime != (timestamp & (~1)):
            return False
        return True

    def import_pyc_file(self, space, modname, filename, buf, pkgpath):
        w = space.wrap
        magic = importing._get_long(buf[:4])
        timestamp = importing._get_long(buf[4:8])
        if (self.check_newer_pyfile(space, filename[:-1], timestamp) or
            not self.check_compatible_mtime(space, filename, timestamp)):
            return self.import_py_file(space, modname, filename[:-1], buf,
                                       pkgpath)
        buf = buf[8:] # XXX ugly copy, should use sequential read instead
        w_mod = w(Module(space, w(modname)))
        real_name = self.name + os.path.sep + filename
        space.setattr(w_mod, w('__loader__'), space.wrap(self))
        importing._prepare_module(space, w_mod, real_name, pkgpath)
        result = importing.load_compiled_module(space, w(modname), w_mod,
                                                filename, magic, timestamp,
                                                buf)
        return result

    def have_modulefile(self, space, filename):
        if ZIPSEP != os.path.sep:
            filename = filename.replace(os.path.sep, ZIPSEP)
        w = space.wrap
        try:
            self.dir.getinfo(filename)
            return True
        except KeyError:
            return False

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
        last_exc = None
        for compiled, is_package, ext in ENUMERATE_EXTS:
            fname = filename + ext
            try:
                buf = self.dir.read(fname)
            except (KeyError, OSError):
                pass
            else:
                if is_package:
                    pkgpath = self.name
                else:
                    pkgpath = None
                try:
                    if compiled:
                        return self.import_pyc_file(space, fullname, fname,
                                                    buf, pkgpath)
                    else:
                        return self.import_py_file(space, fullname, fname,
                                                   buf, pkgpath)
                except OperationError, e:
                    last_exc = e
                    w_mods = space.sys.get('modules')
                space.call_method(w_mods, 'pop', w(fullname), space.w_None)
        if last_exc:
            raise OperationError(self.w_ZipImportError, last_exc.w_value)
        # should never happen I think
        return space.w_None
    load_module.unwrap_spec = ['self', ObjSpace, str]

    def get_data(self, space, filename):
        filename = self._find_relative_path(filename)
        w = space.wrap
        try:
            return w(self.dir.read(filename))
        except (KeyError, OSError):
            raise OperationError(space.w_IOError, space.wrap("Error reading file"))
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
        raise OperationError(self.w_ZipImportError, space.wrap(
            "Cannot find source or code for %s in %s" % (filename, self.name)))
    get_code.unwrap_spec = ['self', ObjSpace, str]

    def get_source(self, space, fullname):
        filename = self.mangle(fullname)
        for compiled, _, ext in ENUMERATE_EXTS:
            if not compiled:
                fname = filename + ext
                if self.have_modulefile(space, fname):
                    return self.get_data(space, fname)
        raise OperationError(self.w_ZipImportError, space.wrap(
            "Cannot find source for %s in %s" % (filename, self.name)))
    get_source.unwrap_spec = ['self', ObjSpace, str]

    def is_package(self, space, fullname):
        filename = self.mangle(fullname)
        for _, is_package, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                return space.wrap(is_package)
        raise OperationError(self.w_ZipImportError, space.wrap(
            "Cannot find module %s in %s" % (filename, self.name)))
    is_package.unwrap_spec = ['self', ObjSpace, str]

    def getarchive(space, self):
        space = self.space
        return space.wrap(self.dir.filename)

def descr_new_zipimporter(space, w_type, name):
    w = space.wrap
    w_ZipImportError = space.getattr(space.getbuiltinmodule('zipimport'),
                                     w('ZipImportError'))
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
            raise OperationError(w_ZipImportError, space.wrap(
                "Cannot find name %s" % (filename,)))
        if not stat.S_ISDIR(s.st_mode):
            ok = True
            break
    if not ok:
        raise OperationError(w_ZipImportError, space.wrap(
            "Did not find %s to be a valid zippath" % (name,)))
    try:
        w_result = zip_cache.get(filename)
        if w_result is None:
            raise OperationError(w_ZipImportError, space.wrap(
                "Cannot import %s from zipfile, recursion detected or"
                "already tried and failed" % (name,)))
        return w_result
    except KeyError:
        zip_cache.cache[filename] = None
    try:
        dir = RZipFile(filename, 'r')
    except (BadZipfile, OSError):
        raise OperationError(w_ZipImportError, space.wrap(
            "%s seems not to be a zipfile" % (filename,)))
    prefix = name[len(filename):]
    if prefix.startswith(os.sep):
        prefix = prefix[1:]
    w_result = space.wrap(W_ZipImporter(space, name, dir, prefix))
    zip_cache.set(filename, w_result)
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
    prefix      = GetSetProperty(W_ZipImporter.getprefix),
)
    
