from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib.objectmodel import we_are_translated
from pypy.module.cpyext.state import State
from pypy.module.cpyext import api
from pypy.rpython.lltypesystem import rffi, lltype

class Module(MixedModule):
    interpleveldefs = {
        'load_module': 'api.load_extension_module',
    }

    appleveldefs = {
    }

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        state = self.space.fromcache(State)
        if not self.space.config.translating:
            state.api_lib = str(api.build_bridge(self.space))
        else:
            api.setup_library(self.space)

    def startup(self, space):
        state = space.fromcache(State)
        from pypy.module.cpyext.typeobject import setup_new_method_def
        from pypy.module.cpyext.pyobject import RefcountState
        setup_new_method_def(space)
        if not we_are_translated():
            space.setattr(space.wrap(self),
                          space.wrap('api_lib'),
                          space.wrap(state.api_lib))
        else:
            refcountstate = space.fromcache(RefcountState)
            refcountstate.init_r2w_from_w2r()

        for func in api.INIT_FUNCTIONS:
            func(space)
            state.check_and_raise_exception()

# import these modules to register api functions by side-effect
import pypy.module.cpyext.thread
import pypy.module.cpyext.pyobject
import pypy.module.cpyext.boolobject
import pypy.module.cpyext.floatobject
import pypy.module.cpyext.modsupport
import pypy.module.cpyext.pythonrun
import pypy.module.cpyext.pyerrors
import pypy.module.cpyext.typeobject
import pypy.module.cpyext.object
import pypy.module.cpyext.stringobject
import pypy.module.cpyext.tupleobject
import pypy.module.cpyext.dictobject
import pypy.module.cpyext.intobject
import pypy.module.cpyext.longobject
import pypy.module.cpyext.listobject
import pypy.module.cpyext.sequence
import pypy.module.cpyext.eval
import pypy.module.cpyext.import_
import pypy.module.cpyext.mapping
import pypy.module.cpyext.iterator
import pypy.module.cpyext.unicodeobject
import pypy.module.cpyext.sysmodule
import pypy.module.cpyext.number
import pypy.module.cpyext.sliceobject
import pypy.module.cpyext.stubsactive
import pypy.module.cpyext.pystate
import pypy.module.cpyext.cdatetime
import pypy.module.cpyext.complexobject
import pypy.module.cpyext.weakrefobject
import pypy.module.cpyext.funcobject
import pypy.module.cpyext.classobject
import pypy.module.cpyext.memoryobject
import pypy.module.cpyext.codecs

# now that all rffi_platform.Struct types are registered, configure them
api.configure_types()
