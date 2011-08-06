from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    """
    This module exposes stacklets directly.
    """

    appleveldefs = {
        'error': 'app_stacklet.error',
    }

    interpleveldefs = {
        'newstacklet': 'interp_stacklet.stacklet_new',
        'Stacklet': 'interp_stacklet.W_Stacklet',
    }
