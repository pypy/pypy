
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'pypy_repr'             : 'interp_magic.pypy_repr',
    }

