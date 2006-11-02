
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'signal': 'interp_signal.signal',
    }

    appleveldefs = {
    }

    def buildloaders(cls):
        from pypy.module.signal import ctypes_signal
        for name in ctypes_signal.signal_names:
            signum = getattr(ctypes_signal, name)
            if signum is not None:
                Module.interpleveldefs[name] = 'space.wrap(%d)' % (signum,)
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

    def __init__(self, space, *args):
        "NOT_RPYTHON"
        from pypy.module.signal.interp_signal import CheckSignalAction
        MixedModule.__init__(self, space, *args)
        # add the signal-checking callback as an action on the space
        space.pending_actions.append(CheckSignalAction(space))
