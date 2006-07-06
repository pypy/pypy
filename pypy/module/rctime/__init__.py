
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'accept2dyear'      : 'interp_time.accept2dyear',
        'time': 'interp_time.time',
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
        # 'floattime'    : 'app_time._floattime'
    }
