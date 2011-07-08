
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    applevel_name = 'numpy'

    interpleveldefs = {
        'array': 'interp_numarray.SingleDimArray',
        'zeros': 'interp_numarray.zeros',
        'empty': 'interp_numarray.zeros',
        'ones': 'interp_numarray.ones',
        'fromstring': 'interp_support.fromstring',

        # ufuncs
        'abs': 'interp_ufuncs.absolute',
        'absolute': 'interp_ufuncs.absolute',
        'copysign': 'interp_ufuncs.copysign',
        'exp': 'interp_ufuncs.exp',
        'floor': 'interp_ufuncs.floor',
        'maximum': 'interp_ufuncs.maximum',
        'minimum': 'interp_ufuncs.minimum',
        'negative': 'interp_ufuncs.negative',
        'reciprocal': 'interp_ufuncs.reciprocal',
        'sign': 'interp_ufuncs.sign',
    }

    appleveldefs = {
        'average': 'app_numpy.average',
        'mean': 'app_numpy.mean',
    }
