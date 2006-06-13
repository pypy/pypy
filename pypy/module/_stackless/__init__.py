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
        'greenlet'   : 'interp_greenlet.AppGreenlet',
    }

    def setup_after_space_initialization(self):
        # post-installing classmethods/staticmethods which
        # are not yet directly supported
        from pypy.module._stackless.coroutine import post_install as post_install_coro
        post_install_coro(self)
        from pypy.module._stackless.interp_greenlet import post_install as post_install_greenlet
        post_install_greenlet(self)

