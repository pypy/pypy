
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import app2interp
from pypy.module.zipimport.rzipfile import is_zipfile
from pypy.interpreter.eval import Code
from pypy.interpreter.module import Module
import os
import stat

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

    def import_py_file(self, space, modname, filename, w_buf):
        w = space.wrap
        # XXX A bit of boilerplatish code stolen from importing.py,
        #     some refactoring to use common code base?
        #     all this error reporting and whatnot
        w_mod = w(Module(space, w(modname)))
        space.sys.setmodule(w_mod)
        space.setattr(w_mod, w('__file__'), w(filename))
        space.setattr(w_mod, w('__doc__'), space.w_None)
        w_mode = w("exec")
        w_code = space.builtin.call('compile', w_buf, w(modname), w_mode)
        pycode = space.interp_w(Code, w_code)
        w_dict = space.getattr(w_mod, w('__dict__'))
        space.call_method(w_dict, 'setdefault',
                          w('__builtins__'),
                          w(space.builtin))
        pycode.exec_code(space, w_dict, w_dict)
        return w_mod

    def get_module(self, space, name):
        w = space.wrap
        try:
            return space.call(space.getattr(self.w_dir, w('getinfo')),
                              space.newlist([w(name)]))
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                # should never happen
                raise e

    def find_module(self, space, import_name, w_path=None):
        import_name = import_name.replace('.', os.path.sep)
        for ext in ['.py', 'pyc', '.pyo']:
            if self.get_module(space, import_name + ext):
                return space.wrap(self)
    find_module.unwrap_spec = ['self', ObjSpace, str, W_Root]

    def load_module(self, space, name):
        w = space.wrap
        filename = name.replace('.', os.path.sep) + '.py'
        w_buf = space.call(space.getattr(self.w_dir, w('read')),
                           space.newlist([w(filename)]))
        return self.import_py_file(space, name, filename, w_buf)
    load_module.unwrap_spec = ['self', ObjSpace, str]

def descr_new_zipimporter(space, w_type, name):
    try:
        s = os.stat(name)
    except OSError:
        return
    if stat.S_ISDIR(s.st_mode):
        return
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
        return None
    return space.wrap(W_ZipImporter(space, name, w_dir, w_zipfile))
    
descr_new_zipimporter.unwrap_spec = [ObjSpace, W_Root, str]

W_ZipImporter.typedef = TypeDef(
    'zipimporter',
    __new__     = interp2app(descr_new_zipimporter),
    find_module = interp2app(W_ZipImporter.find_module),
    load_module = interp2app(W_ZipImporter.load_module),
)
