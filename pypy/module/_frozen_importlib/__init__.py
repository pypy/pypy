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

    @staticmethod
    def _compile_bootstrap_module(space, name, w_name, w_dict):
        """NOT_RPYTHON"""
        ec = space.getexecutioncontext()
        with open(os.path.join(lib_python, 'importlib', name + '.py')) as fp:
            source = fp.read()
        pathname = "<frozen importlib.%s>" % name
        code_w = ec.compiler.compile(source, pathname, 'exec', 0)
        space.setitem(w_dict, space.wrap('__name__'), w_name)
        space.setitem(w_dict, space.wrap('__builtins__'),
                      space.wrap(space.builtin))
        code_w.exec_code(space, w_dict, w_dict)

    def install(self):
        """NOT_RPYTHON"""
        super(Module, self).install()
        space = self.space
        # "import importlib/_boostrap_external.py"
        w_mod = Module(space, space.wrap("_frozen_importlib_external"))
        self._compile_bootstrap_module(
            space, '_bootstrap_external', w_mod.w_name, w_mod.w_dict)
        space.sys.setmodule(w_mod)
        # "from importlib/_boostrap.py import *"
        # It's not a plain "import importlib._boostrap", because we
        # don't want to freeze importlib.__init__.
        self._compile_bootstrap_module(
            space, '_bootstrap', self.w_name, self.w_dict)

        self.w_import = space.wrap(interp_import.import_with_frames_removed)

    def startup(self, space):
        """Copy our __import__ to builtins."""
        w_install = self.getdictvalue(space, '_install')
        space.call_function(w_install,
                            space.getbuiltinmodule('sys'),
                            space.getbuiltinmodule('_imp'))
        self.space.builtin.setdictvalue(space, '__import__', self.w_import)
