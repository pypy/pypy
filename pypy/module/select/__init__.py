# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import select
import sys


class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'poll'  : 'interp_select.poll',
        'select': 'interp_select.select',
        'error' : 'space.fromcache(interp_select.Cache).w_error'
    }

    # TODO: this doesn't feel right...
    if hasattr(select, "epoll"):
        interpleveldefs['epoll'] = 'interp_epoll.W_Epoll'
        symbols = [
            "EPOLLIN", "EPOLLOUT", "EPOLLPRI", "EPOLLERR", "EPOLLHUP",
            "EPOLLET", "EPOLLONESHOT", "EPOLLRDNORM", "EPOLLRDBAND",
            "EPOLLWRNORM", "EPOLLWRBAND", "EPOLLMSG"
        ]
        for symbol in symbols:
            if hasattr(select, symbol):
                interpleveldefs[symbol] = "space.wrap(%s)" % getattr(select, symbol)


    def buildloaders(cls):
        from pypy.rlib import rpoll
        for name in rpoll.eventnames:
            value = getattr(rpoll, name)
            Module.interpleveldefs[name] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
