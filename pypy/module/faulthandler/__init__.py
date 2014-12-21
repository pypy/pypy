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

        '_read_null': 'interp_faulthandler.read_null',
        '_sigsegv': 'interp_faulthandler.sigsegv',
        '_sigfpe': 'interp_faulthandler.sigfpe',
        '_sigabrt': 'interp_faulthandler.sigabrt',
        '_sigbus': 'interp_faulthandler.sigbus',
        '_sigill': 'interp_faulthandler.sigill',
        '_fatal_error': 'interp_faulthandler.fatal_error',
    }
