from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'set_param':    'interp_jit.set_param',
        'get_optimizer_name': 'interp_jit.get_optimizer_name',
    }

    def setup_after_space_initialization(self):
        # force the __extend__ hacks to occur early
        import pypy.module.pypyjit.interp_jit
