
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
        'add': 'interp_ufuncs.add',
        'copysign': 'interp_ufuncs.copysign',
        'divide': 'interp_ufuncs.divide',
        'exp': 'interp_ufuncs.exp',
        'fabs': 'interp_ufuncs.fabs',
        'floor': 'interp_ufuncs.floor',
        'maximum': 'interp_ufuncs.maximum',
        'minimum': 'interp_ufuncs.minimum',
        'multiply': 'interp_ufuncs.multiply',
        'negative': 'interp_ufuncs.negative',
        'reciprocal': 'interp_ufuncs.reciprocal',
        'sign': 'interp_ufuncs.sign',
        'subtract': 'interp_ufuncs.subtract',
    }

    appleveldefs = {
        'average': 'app_numpy.average',
        'mean': 'app_numpy.mean',
    }
