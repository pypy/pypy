from rpython.rlib.objectmodel import we_are_translated
from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.frozenmodule import compile_bootstrap_module
from pypy.module.sys import initpath
from pypy.module._frozen_importlib import interp_import

class Module(MixedModule):
    interpleveldefs = {
        }

    appleveldefs = {
        }

    def install(self):
        """NOT_RPYTHON"""
        from pypy.module.imp import interp_imp

        super(Module, self).install()
        space = self.space
        # "import importlib/_boostrap_external.py"
        w_mod = Module(space, space.wrap("_frozen_importlib_external"))
        # hack: inject MAGIC_NUMBER into this module's dict
        space.setattr(w_mod, space.wrap('MAGIC_NUMBER'),
                      interp_imp.get_magic(space))
        compile_bootstrap_module(
            space, '_bootstrap_external', w_mod.w_name, w_mod.w_dict)
        space.sys.setmodule(w_mod)
        # "from importlib/_boostrap.py import *"
        # It's not a plain "import importlib._boostrap", because we
        # don't want to freeze importlib.__init__.
        compile_bootstrap_module(
            space, '_bootstrap', self.w_name, self.w_dict)

        self.w_import = space.wrap(interp_import.import_with_frames_removed)

    def startup(self, space):
        """Copy our __import__ to builtins."""
        if not we_are_translated():
            self.startup_at_translation_time_only(space)
        # use special module api to prevent a cell from being introduced
        self.space.builtin.setdictvalue_dont_introduce_cell(
            '__import__', self.w_import)

    def startup_at_translation_time_only(self, space):
        # Issue #2834
        # Call _bootstrap._install() at translation time only, not at
        # runtime.  By looking around what it does, this should not
        # freeze any machine-specific paths.  I *think* it only sets up
        # stuff that depends on the platform.
        w_install = self.getdictvalue(space, '_install')
        space.call_function(w_install,
                            space.getbuiltinmodule('sys'),
                            space.getbuiltinmodule('_imp'))
        w_install_external = self.getdictvalue(
            space, '_install_external_importers')
        space.call_function(w_install_external)
