from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        }
    
    interpleveldefs = {
        'IEEE_CONTEXT_MAX_BITS': 'space.wrap(interp_decimal.IEEE_CONTEXT_MAX_BITS)',
        }
