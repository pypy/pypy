from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'set_param':    'interp_jit.set_param',
        'residual_call': 'interp_jit.residual_call',
        'set_compile_hook': 'interp_jit.set_compile_hook',
    }

    def setup_after_space_initialization(self):
        # force the __extend__ hacks to occur early
        import pypy.module.pypyjit.interp_jit
        # add the 'defaults' attribute
        from pypy.rlib.jit import PARAMETERS
        space = self.space
        w_obj = space.wrap(PARAMETERS)
        space.setattr(space.wrap(self), space.wrap('defaults'), w_obj)
