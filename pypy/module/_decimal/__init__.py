from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        }
    
    interpleveldefs = {
        'Decimal': 'interp_decimal.W_Decimal',
        'getcontext': 'interp_context.getcontext',
        'IEEE_CONTEXT_MAX_BITS': 'space.wrap(interp_decimal.IEEE_CONTEXT_MAX_BITS)',
        }
