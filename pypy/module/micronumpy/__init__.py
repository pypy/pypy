
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    applevel_name = 'numpy'
    
    interpleveldefs = {
        'array': 'numarray.SingleDimArray',
    }

    appleveldefs = {}
