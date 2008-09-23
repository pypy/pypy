
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'signal':              'interp_signal.signal',
        'getsignal':           'interp_signal.getsignal',
        'NSIG':                'space.wrap(interp_signal.NSIG)',
        'SIG_DFL':             'space.wrap(interp_signal.SIG_DFL)',
        'SIG_IGN':             'space.wrap(interp_signal.SIG_IGN)',
    }

    appleveldefs = {
        'default_int_handler': 'app_signal.default_int_handler',
    }

    def buildloaders(cls):
        from pypy.module.signal import interp_signal
        for name in interp_signal.signal_names:
            signum = getattr(interp_signal, name)
            if signum is not None:
                Module.interpleveldefs[name] = 'space.wrap(%d)' % (signum,)
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

    def __init__(self, space, *args):
        "NOT_RPYTHON"
        from pypy.module.signal import interp_signal
        MixedModule.__init__(self, space, *args)
        # add the signal-checking callback as an action on the space
        space.check_signal_action = interp_signal.CheckSignalAction(space)
        space.actionflag.register_action(space.check_signal_action)
        # use the C-level pypysig_occurred variable as the action flag
        # (the result is that the C-level signal handler will directly
        # set the flag for the CheckSignalAction)
        space.actionflag.__class__ = interp_signal.SignalActionFlag
        # xxx yes I know the previous line is a hack
