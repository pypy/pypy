from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """A demo built-in module based on ctypes."""

    interpleveldefs = {
        'clock'    : 'interp_time.clock',
    }

    appleveldefs = {
    }
