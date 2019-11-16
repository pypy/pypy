from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'load': 'interp_hpy.descr_load'
    }
    appleveldefs = {}
