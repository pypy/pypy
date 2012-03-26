# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import sys


class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'poll'  : 'interp_select.poll',
        'select': 'interp_select.select',
        'error' : 'space.fromcache(interp_select.Cache).w_error'
    }

    if sys.platform.startswith('linux'):
        interpleveldefs['epoll'] = 'interp_epoll.W_Epoll'
        from pypy.module.select.interp_epoll import cconfig, public_symbols
        for symbol in public_symbols:
            value = cconfig[symbol]
            if value is not None:
                interpleveldefs[symbol] = "space.wrap(%r)" % value

    if 'bsd' in sys.platform or sys.platform.startswith('darwin'):
        interpleveldefs["kqueue"] = "interp_kqueue.W_Kqueue"
        interpleveldefs["kevent"] = "interp_kqueue.W_Kevent"
        from pypy.module.select.interp_kqueue import symbol_map
        for symbol in symbol_map:
            interpleveldefs[symbol] = "space.wrap(interp_kqueue.%s)" % symbol

    def buildloaders(cls):
        from pypy.rlib import rpoll
        for name in rpoll.eventnames:
            value = getattr(rpoll, name)
            Module.interpleveldefs[name] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
