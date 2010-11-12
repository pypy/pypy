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

    def startup(self, space):
        space.fromcache(State).startup(space)

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
