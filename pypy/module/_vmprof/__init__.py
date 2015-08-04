from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    VMProf for PyPy: a statistical profiler
    """
    appleveldefs = {
    }

    interpleveldefs = {
        'enable': 'interp_vmprof.enable',
        'disable': 'interp_vmprof.disable',
        'error': 'space.fromcache(interp_vmprof.Cache).w_error',
    }
