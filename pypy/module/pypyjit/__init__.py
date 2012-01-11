from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'set_param':    'interp_jit.set_param',
        'residual_call': 'interp_jit.residual_call',
        'set_compile_hook': 'interp_resop.set_compile_hook',
        'set_optimize_hook': 'interp_resop.set_optimize_hook',
        'set_abort_hook': 'interp_resop.set_abort_hook',
        'ResOperation': 'interp_resop.WrappedOp',
        'Box': 'interp_resop.WrappedBox',
    }

    def setup_after_space_initialization(self):
        # force the __extend__ hacks to occur early
        from pypy.module.pypyjit.interp_jit import pypyjitdriver
        from pypy.module.pypyjit.policy import pypy_hooks
        # add the 'defaults' attribute
        from pypy.rlib.jit import PARAMETERS
        space = self.space
        pypyjitdriver.space = space
        w_obj = space.wrap(PARAMETERS)
        space.setattr(space.wrap(self), space.wrap('defaults'), w_obj)
        pypy_hooks.space = space
