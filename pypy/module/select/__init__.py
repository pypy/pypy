# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
import sys

class Module(MixedModule):
    appleveldefs = {
        'error': 'app_select.error',
    }

    interpleveldefs = {
        'poll'  :  'interp_select.poll',
        'select': 'interp_select.select',
    }

    def buildloaders(cls):
        from pypy.rlib import rpoll
        for name in rpoll.eventnames:
            value = getattr(rpoll, name)
            Module.interpleveldefs[name] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

