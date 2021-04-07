from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {}

    interpleveldefs = {
        'load_from_spec': 'interp_hpy.descr_load_from_spec',
        'load': 'interp_hpy.descr_load',
        'get_version': 'interp_hpy.descr_get_version',
    }

    def __init__(self, space, *args):
        from pypy.module._hpy_universal.interp_hpy import init_hpy_module
        MixedModule.__init__(self, space, *args)
        init_hpy_module(space)
