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
        'coroutine'  : 'coroutine.AppCoroutine',
    }

    def setup_after_space_initialization(self):
        # post-installing classmethods/staticmethods which
        # are not yet directly supported
        from pypy.module.stackless.coroutine import post_install
        post_install(self)
