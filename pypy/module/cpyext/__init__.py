from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib.objectmodel import we_are_translated
import pypy.module.cpyext.api

class State:
    def __init__(self, space):
        if not we_are_translated():
            self.api_lib = str(api.build_bridge(space))
        else:
            XXX # build an import library when translating pypy.

class Module(MixedModule):
    interpleveldefs = {
    }

    appleveldefs = {
    }

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        state = self.space.fromcache(State)

    def startup(self, space):
        state = space.fromcache(State)
        space.setattr(space.wrap(self),
                      space.wrap('api_lib'),
                      space.wrap(state.api_lib))

# import these modules to register api functions by side-effect
import pypy.module.cpyext.modsupport
import pypy.module.cpyext.pythonrun


