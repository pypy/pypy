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
        from pypy.module.select import ctypes_select as _c 
        for constant, value in _c.constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

