
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    applevel_name = 'numpy'
    
    interpleveldefs = {
        'zeros'    : 'numarray.zeros',
        }

    appleveldefs = {}
