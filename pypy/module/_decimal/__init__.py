from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        }
    
    interpleveldefs = {
        'Decimal': 'interp_decimal.W_Decimal',
        'getcontext': 'interp_context.getcontext',

        'IEEE_CONTEXT_MAX_BITS': 'space.wrap(interp_decimal.IEEE_CONTEXT_MAX_BITS)',
        }
    for name in ('DecimalException', 'Clamped', 'Rounded', 'Inexact',
                 'Subnormal', 'Underflow', 'Overflow', 'DivisionByZero',
                 'InvalidOperation', 'FloatOperation'):
        interpleveldefs[name] = 'interp_signals.get(space).w_%s' % name
        
