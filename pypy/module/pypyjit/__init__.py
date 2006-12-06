from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'enable': 'interp_jit.enable',
    }

    def setup_after_space_initialization(self):
        # force the setup() to run early
        import pypy.module.pypyjit.interp_jit
