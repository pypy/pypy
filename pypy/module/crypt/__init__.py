from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """A demo built-in module based on ctypes."""

    interpleveldefs = {
        'crypt'    : 'interp_crypt.crypt',
    }

    appleveldefs = {
    }
