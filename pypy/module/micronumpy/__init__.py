
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    applevel_name = 'numpy'

    interpleveldefs = {
        'array': 'interp_numarray.SingleDimArray',
        'zeros': 'interp_numarray.zeros',

        # ufuncs
        'abs': 'interp_ufuncs.npabs',
        'negative': 'interp_ufuncs.negative',
    }

    appleveldefs = {}
