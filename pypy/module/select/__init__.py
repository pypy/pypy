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
        interpleveldefs["epoll"] = "interp_epoll.W_Epoll"
        for symbol in [
            "EPOLLIN", "EPOLLOUT", "EPOLLPRI", "EPOLLERR", "EPOLLHUP",
            "EPOLLET", "EPOLLONESHOT", "EPOLLRDNORM", "EPOLLRDBAND",
            "EPOLLWRNORM", "EPOLLWRBAND", "EPOLLMSG"
        ]:
            if hasattr(select, symbol):
                interpleveldefs[symbol] = "space.wrap(%s)" % getattr(select, symbol)

    if hasattr(select, "kqueue"):
        interpleveldefs["kqueue"] = "interp_kqueue.W_Kqueue"
        interpleveldefs["kevent"] = "interp_kqueue.W_Kevent"

        for symbol in ["KQ_FILTER_READ", "KQ_FILTER_WRITE", "KQ_EV_ADD", "KQ_EV_ONESHOT", "KQ_EV_ENABLE"]:
            interpleveldefs[symbol] = "space.wrap(interp_kqueue.%s)" % symbol


    def buildloaders(cls):
        from pypy.rlib import rpoll
        for name in rpoll.eventnames:
            value = getattr(rpoll, name)
            Module.interpleveldefs[name] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
