# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module implements Stackless for applications.
    """

    appleveldefs = {
        'GreenletExit' : 'app_greenlet.GreenletExit',
        'GreenletError' : 'app_greenlet.GreenletError',
    }

    interpleveldefs = {
        'tasklet'    : 'interp_stackless.tasklet',
        'coroutine'  : 'coroutine.AppCoroutine',
        'clonable'   : 'interp_clonable.ClonableCoroutine',
        'greenlet'   : 'interp_greenlet.AppGreenlet',
    }

    def setup_after_space_initialization(self):
        # post-installing classmethods/staticmethods which
        # are not yet directly supported
        from pypy.module._stackless.coroutine import post_install as post_install_coro
        post_install_coro(self)
        from pypy.module._stackless.interp_clonable import post_install as post_install_clonable
        post_install_clonable(self)
        from pypy.module._stackless.interp_greenlet import post_install as post_install_greenlet
        post_install_greenlet(self)

