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
        'coroutine'  : 'interp_coroutine.AppCoroutine',
        'greenlet'   : 'interp_greenlet.AppGreenlet',
        'usercostate': 'interp_composable_coroutine.W_UserCoState',
        '_return_main' : 'interp_coroutine.return_main',
    }

    def setup_after_space_initialization(self):
        # post-installing classmethods/staticmethods which
        # are not yet directly supported
        from pypy.module._stackless.interp_coroutine import post_install as post_install_coro
        post_install_coro(self)
        from pypy.module._stackless.interp_greenlet import post_install as post_install_greenlet
        post_install_greenlet(self)

        if self.space.config.translation.gc == 'marksweep':
            from pypy.module._stackless.interp_clonable import post_install as post_install_clonable
            self.extra_interpdef('clonable', 'interp_clonable.AppClonableCoroutine')
            self.extra_interpdef('fork',     'interp_clonable.fork')
            post_install_clonable(self)
