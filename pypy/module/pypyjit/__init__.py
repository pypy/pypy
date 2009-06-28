from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'set_param':    'interp_jit.set_param',
    }

    def setup_after_space_initialization(self):
        # force the __extend__ hacks to occur early
        import pypy.module.pypyjit.interp_jit
