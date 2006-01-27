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

    def setup_after_space_initialization(self):
        # post-installing classmethods/staticmethods which
        # are not yet directly supported
        from pypy.module.stackless.interp_coroutine import post_install
        post_install(self)
