from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'enable': 'interp_faulthandler.enable',
        'disable': 'interp_faulthandler.disable',
        'is_enabled': 'interp_faulthandler.is_enabled',
        'register': 'interp_faulthandler.register',

        'dump_traceback': 'interp_faulthandler.dump_traceback',
    }
