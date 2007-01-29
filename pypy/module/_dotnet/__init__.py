# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """CLR module"""

    appleveldefs = {}
    
    interpleveldefs = {
        '_CliObject_internal': 'interp_dotnet.W_CliObject',
        'call_staticmethod': 'interp_dotnet.call_staticmethod',
        'load_cli_class': 'interp_dotnet.load_cli_class',
    }
