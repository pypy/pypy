
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'pypy_repr'             : 'interp_magic.pypy_repr',
        'isfake'                : 'interp_magic.isfake',
        'interp_pdb'            : 'interp_magic.interp_pdb',
        'method_cache_counter'  : 'interp_magic.method_cache_counter',
        'reset_method_cache_counter'  : 'interp_magic.reset_method_cache_counter',
    }
