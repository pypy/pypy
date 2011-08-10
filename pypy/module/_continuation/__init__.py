from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    """
    This module exposes 'continuations'.
    """

    appleveldefs = {
        'error': 'app_continuation.error',
    }

    interpleveldefs = {
        'new': 'interp_continuation.stacklet_new',
        'callcc': 'interp_continuation.stacklet_new',     # a synonym
        'Continuation': 'interp_continuation.W_Stacklet',
    }
