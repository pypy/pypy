# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module implements Stackless for applications.
    """

    appleveldefs = {
    }

    interpleveldefs = {
        'tasklet'    : 'interp_stackless.tasklet',
        'Coroutine'  : 'interp_coroutine.AppCoroutine',
    }
