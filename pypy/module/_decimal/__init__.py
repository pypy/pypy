from pypy.interpreter.mixedmodule import MixedModule
from rpython.rlib import rmpdec
from pypy.module._decimal import interp_signals


class Module(MixedModule):
    appleveldefs = {
        }
    
    interpleveldefs = {
        'Decimal': 'interp_decimal.W_Decimal',
        'Context': 'interp_context.W_Context',
        'getcontext': 'interp_context.getcontext',
        'setcontext': 'interp_context.setcontext',
        'DecimalException': 'interp_signals.get(space).w_DecimalException',

        'IEEE_CONTEXT_MAX_BITS': 'space.wrap(interp_decimal.IEEE_CONTEXT_MAX_BITS)',
        'MAX_PREC': 'space.wrap(interp_decimal.MAX_PREC)',
        }
    for name in rmpdec.ROUND_CONSTANTS:
        interpleveldefs[name] = 'space.wrap(%r)' % name
    for name, flag in interp_signals.SIGNAL_MAP:
        interpleveldefs[name] = 'interp_signals.get(space).w_%s' % name
        
