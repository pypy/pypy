
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'pypy_repr'             : 'interp_magic.pypy_repr',
        'isfake'                : 'interp_magic.isfake',
        'interp_pdb'            : 'interp_magic.interp_pdb',
    }
