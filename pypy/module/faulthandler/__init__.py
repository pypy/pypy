from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'enable': 'handler.enable',
        'disable': 'handler.disable',
        'is_enabled': 'handler.is_enabled',
#        'register': 'interp_faulthandler.register',
#
        'dump_traceback': 'handler.dump_traceback',
#
        '_read_null': 'handler.read_null',
        '_sigsegv': 'handler.sigsegv',
        '_sigfpe': 'handler.sigfpe',
        '_sigabrt': 'handler.sigabrt',
        '_stack_overflow': 'handler.stack_overflow',
    }

    def shutdown(self, space):
        from pypy.module.faulthandler import handler
        handler.finish(space)
        MixedModule.shutdown(self, space)
