from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'enable': 'interp_faulthandler.enable',
        'register': 'interp_faulthandler.register',
    }
