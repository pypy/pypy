from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
        'enable': 'app_gc.enable',
        'disable': 'app_gc.disable',
        'isenabled': 'app_gc.isenabled',
    }
    interpleveldefs = {
        'collect': 'interp_gc.collect',
        'estimate_heap_size': 'interp_gc.estimate_heap_size',
    }
