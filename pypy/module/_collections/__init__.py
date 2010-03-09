import py

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {}
  
    interpleveldefs = {
        'identity_dict'          : 'interp_collection.W_IdentityDict',
        }
    
