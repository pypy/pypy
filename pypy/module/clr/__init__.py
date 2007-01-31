# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import boxing_rules # with side effects

class Module(MixedModule):
    """CLR module"""

    appleveldefs = {}
    
    interpleveldefs = {
        '_CliObject_internal': 'interp_clr.W_CliObject',
        'call_staticmethod': 'interp_clr.call_staticmethod',
        'load_cli_class': 'interp_clr.load_cli_class',
    }
