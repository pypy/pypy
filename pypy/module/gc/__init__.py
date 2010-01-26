from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
        'enable': 'app_gc.enable',
        'disable': 'app_gc.disable',
        'isenabled': 'app_gc.isenabled',
    }
    interpleveldefs = {
        'collect': 'interp_gc.collect',
        'enable_finalizers': 'interp_gc.enable_finalizers',
        'disable_finalizers': 'interp_gc.disable_finalizers',
        'estimate_heap_size': 'interp_gc.estimate_heap_size',
        'garbage' : 'space.newlist([])',
        #'dump_heap_stats': 'interp_gc.dump_heap_stats',
    }

    def __init__(self, space, w_name):
        ts = space.config.translation.type_system
        if ts == 'ootype':
            del self.interpleveldefs['dump_heap_stats']
        MixedModule.__init__(self, space, w_name)
