from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib.objectmodel import we_are_translated
import pypy.module.cpyext.api
from pypy.module.cpyext.state import State


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
import pypy.module.cpyext.floatobject
import pypy.module.cpyext.modsupport
import pypy.module.cpyext.pythonrun
api.configure()
