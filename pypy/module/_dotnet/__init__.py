# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """CLR module"""

    appleveldefs = {
        'ArrayList': 'app_dotnet.ArrayList',
        'Math': 'app_dotnet.Math',
    }
    
    interpleveldefs = {
        '_CliObject_internal': 'interp_dotnet.W_CliObject',
        'call_staticmethod': 'interp_dotnet.call_staticmethod',
    }
