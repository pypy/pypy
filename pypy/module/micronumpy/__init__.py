
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    applevel_name = 'numpy'

    interpleveldefs = {
        'array': 'interp_numarray.SingleDimArray',
        'zeros': 'interp_numarray.zeros',

        # ufuncs
        'negative': 'interp_ufuncs.negative',
    }

    appleveldefs = {}
