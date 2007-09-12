from pypy.interpreter.mixedmodule import MixedModule, SkipModule
    
class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'ref': 'interp__weakref.W_Weakref',
        'getweakrefcount': 'interp__weakref.getweakrefcount',
        'getweakrefs': 'interp__weakref.getweakrefs',
        'ReferenceType': 'interp__weakref.W_Weakref',
        'ProxyType': 'interp__weakref.W_Proxy', 
        'CallableProxyType': 'interp__weakref.W_CallableProxy',
        'proxy': 'interp__weakref.proxy'
    }

    def __init__(self, space, *args):
        if not space.config.translation.rweakref:
            raise SkipModule("no RPython-level weakrefs")
        MixedModule.__init__(self, space, *args)
