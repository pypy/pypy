from pypy.interpreter.mixedmodule import MixedModule
from rpython.rlib import rmpdec

class Module(MixedModule):
    appleveldefs = {
        }
    
    interpleveldefs = {
        'Decimal': 'interp_decimal.W_Decimal',
        'Context': 'interp_context.W_Context',
        'getcontext': 'interp_context.getcontext',
        'setcontext': 'interp_context.setcontext',

        'IEEE_CONTEXT_MAX_BITS': 'space.wrap(interp_decimal.IEEE_CONTEXT_MAX_BITS)',
        }
    for name in rmpdec.ROUND_CONSTANTS:
        interpleveldefs[name] = 'space.wrap(%r)' % (
            getattr(rmpdec, 'MPD_' + name),)
    for name in ('DecimalException', 'Clamped', 'Rounded', 'Inexact',
                 'Subnormal', 'Underflow', 'Overflow', 'DivisionByZero',
                 'InvalidOperation', 'FloatOperation'):
        interpleveldefs[name] = 'interp_signals.get(space).w_%s' % name
        
