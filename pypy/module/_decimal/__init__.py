from pypy.interpreter.mixedmodule import MixedModule
from rpython.rlib import rmpdec
from pypy.module._decimal import interp_signals


class Module(MixedModule):
    appleveldefs = {
        'localcontext': 'app_context.localcontext',
        }
    
    interpleveldefs = {
        'Decimal': 'interp_decimal.W_Decimal',
        'Context': 'interp_context.W_Context',
        'DefaultContext': 'interp_context.W_Context(space)',
        'getcontext': 'interp_context.getcontext',
        'setcontext': 'interp_context.setcontext',
        'DecimalException': 'interp_signals.get(space).w_DecimalException',
        'SignalTuple': 'interp_signals.get(space).w_SignalTuple',

        'IEEE_CONTEXT_MAX_BITS': 'space.wrap(interp_decimal.IEEE_CONTEXT_MAX_BITS)',
        'MAX_PREC': 'space.wrap(interp_decimal.MAX_PREC)',
        'MAX_EMAX': 'space.wrap(interp_decimal.MAX_EMAX)',
        'MIN_EMIN': 'space.wrap(interp_decimal.MIN_EMIN)',
        'MIN_ETINY': 'space.wrap(interp_decimal.MIN_ETINY)',

        'HAVE_THREADS': 'space.wrap(space.config.translation.thread)',
        }
    for name in rmpdec.ROUND_CONSTANTS:
        interpleveldefs[name] = 'space.wrap(%r)' % name
    for name, flag in interp_signals.SIGNAL_MAP:
        interpleveldefs[name] = 'interp_signals.get(space).w_%s' % name
    for name, flag in interp_signals.COND_MAP:
        interpleveldefs[name] = 'interp_signals.get(space).w_%s' % name
        
