from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    Write me :)
    """
    appleveldefs = {
    }

    interpleveldefs = {
        'enable': 'interp_vmprof.enable',
        'disable': 'interp_vmprof.disable',
    }

    def setup_after_space_initialization(self):
        # force the __extend__ hacks to occur early
        from pypy.module._vmprof.interp_vmprof import VMProf
        self.vmprof = VMProf()
