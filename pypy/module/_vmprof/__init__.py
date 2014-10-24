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
