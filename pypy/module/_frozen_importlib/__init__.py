import os
from pypy.interpreter.mixedmodule import MixedModule
from pypy.module.sys import initpath
from pypy.module._frozen_importlib import interp_import

lib_python = os.path.join(os.path.dirname(__file__),
                          '..', '..', '..', 'lib-python', '3')

class Module(MixedModule):
    interpleveldefs = {
        }

    appleveldefs = {
        }

    def install(self):
        """NOT_RPYTHON"""
        super(Module, self).install()
        space = self.space
        # "from importlib/_boostrap.py import *"
        # It's not a plain "import importlib._boostrap", because we
        # don't want to freeze importlib.__init__.
        with open(os.path.join(lib_python, 'importlib', '_bootstrap.py')) as fp:
            source = fp.read()
        pathname = "<frozen importlib._bootstrap>"
        code_w = self._cached_compile(source, pathname, 'exec', 0)
        space.setitem(self.w_dict, space.wrap('__name__'), self.w_name)
        space.setitem(self.w_dict, space.wrap('__builtins__'),
                      space.wrap(space.builtin))
        code_w.exec_code(space, self.w_dict, self.w_dict)

        self.w_import = space.wrap(interp_import.import_with_frames_removed)

    def _cached_compile(self, source, *args):
        from rpython.config.translationoption import CACHE_DIR
        from pypy.module.marshal import interp_marshal

        space = self.space
        cachename = os.path.join(CACHE_DIR, 'frozen_importlib_bootstrap')
        try:
            if space.config.translating:
                raise IOError("don't use the cache when translating pypy")
            with open(cachename, 'rb') as f:
                previous = f.read(len(source) + 1)
                if previous != source + '\x00':
                    raise IOError("source changed")
                w_bin = space.newbytes(f.read())
                code_w = interp_marshal.loads(space, w_bin)
        except IOError:
            # must (re)compile the source
            ec = space.getexecutioncontext()
            code_w = ec.compiler.compile(source, *args)
            w_bin = interp_marshal.dumps(space, code_w, space.wrap(2))
            content = source + '\x00' + space.bytes_w(w_bin)
            with open(cachename, 'wb') as f:
                f.write(content)
        return code_w

    def startup(self, space):
        """Copy our __import__ to builtins."""
        w_install = self.getdictvalue(space, '_install')
        space.call_function(w_install,
                            space.getbuiltinmodule('sys'),
                            space.getbuiltinmodule('_imp'))
        self.space.builtin.setdictvalue(space, '__import__', self.w_import)
