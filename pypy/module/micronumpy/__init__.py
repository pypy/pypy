
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    applevel_name = 'numpy'
    
    interpleveldefs = {
        'zeros'    : 'numarray.zeros',
        'minimum'  : 'ufunc.minimum',
        }

    appleveldefs = {}
