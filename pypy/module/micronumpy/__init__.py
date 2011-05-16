
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    applevel_name = 'numpy'

    interpleveldefs = {
        'array': 'interp_numarray.SingleDimArray',
        'zeros': 'interp_numarray.zeros',

        # ufuncs
        'absolute': 'interp_ufuncs.absolute',
        'negative': 'interp_ufuncs.negative',
        'minimum': 'interp_ufuncs.minimum',
        'maximum': 'interp_ufuncs.maximum',
    }

    appleveldefs = {}
