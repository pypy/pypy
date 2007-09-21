# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
import sys

class Module(MixedModule):
    appleveldefs = {
        'error': 'app_select.error',
        'select': 'app_select.select',
    }

    interpleveldefs = {
        'poll'  :  'interp_select.poll',
    }

    def buildloaders(cls):
        constantnames = '''
            POLLIN POLLPRI POLLOUT POLLERR POLLHUP POLLNVAL
            POLLRDNORM POLLRDBAND POLLWRNORM POLLWEBAND POLLMSG'''.split()

        from _rsocket_ctypes import constants
        for name in constantnames:
            if name in constants:
                value = constants[name]
                Module.interpleveldefs[name] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

