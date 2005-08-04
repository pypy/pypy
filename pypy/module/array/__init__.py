from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
         '__doc__' :  'app_array.__doc__',
         '__name__' :  'app_array.__name__',
         'array' :  'app_array.array',
         'ArrayType' :  'app_array.ArrayType',
    }
    interpleveldefs = {
    }
