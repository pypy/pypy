
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'accept2dyear': 'interp_time.accept2dyear',
        'time': 'interp_time.time',
        'clock': 'interp_time.clock',
        'ctime': 'interp_time.ctime',
        'gmtime': 'interp_time.gmtime',
        'localtime': 'interp_time.localtime',
        'mktime': 'interp_time.mktime',
    }

    # def init(self, space):
#         from pypy.module.rctime import interp_time
#         interp_time.init_module(space)
#         
    def buildloaders(cls):
        from pypy.module.rctime import interp_time
        Module.interpleveldefs["accept2dyear"] = 'space.wrap(%r)' % interp_time._init_accept2dyear()
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

    appleveldefs = {
        'sleep': 'app_time.sleep',
        '_check_float': 'app_time._check_float',
        'struct_time': 'app_time.struct_time'   
    }
