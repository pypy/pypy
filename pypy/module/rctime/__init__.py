
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'accept2dyear': 'interp_time.accept2dyear',
        'timezone': 'interp_time.timezone',
        'daylight': 'interp_time.daylight',
        'tzname': 'interp_time.tzname',
        'altzone': 'interp_time.altzone',
        'time': 'interp_time.time',
        'clock': 'interp_time.clock',
        'ctime': 'interp_time.ctime',
        'asctime': 'interp_time.asctime',
        'gmtime': 'interp_time.gmtime',
        'localtime': 'interp_time.localtime',
        'mktime': 'interp_time.mktime',
        'tzset': 'interp_time.tzset'
    }

    # def init(self, space):
#         from pypy.module.rctime import interp_time
#         interp_time.init_module(space)
#         
    def buildloaders(cls):
        from pypy.module.rctime import interp_time

        # this machinery is needed to expose constants
        # that have to be initialized one time only
        
        Module.interpleveldefs["accept2dyear"] = 'space.wrap(%r)' %\
            interp_time._init_accept2dyear()
        
        timezone, daylight, tzname, altzone = interp_time._init_timezone()
        Module.interpleveldefs['timezone'] = 'space.wrap(%r)' % timezone
        Module.interpleveldefs['daylight'] = 'space.wrap(%r)' % daylight
        Module.interpleveldefs['tzname'] = \
            'space.newlist([space.wrap(%r), space.wrap(%r)])' % tuple(tzname)
        Module.interpleveldefs['altzone'] = 'space.wrap(%r)' % altzone
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

    appleveldefs = {
        'sleep': 'app_time.sleep',
        '_check_float': 'app_time._check_float',
        'struct_time': 'app_time.struct_time',
        '__doc__': 'app_time.__doc__'
    }
