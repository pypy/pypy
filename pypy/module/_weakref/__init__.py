from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'ref': 'interp__weakref.W_Weakref',
        'getweakrefcount': 'interp__weakref.getweakrefcount',
        'getweakrefs': 'interp__weakref.getweakrefs',
        'ReferenceType': 'interp__weakref.W_Weakref',
    }
