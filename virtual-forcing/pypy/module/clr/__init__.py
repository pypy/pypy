# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import boxing_rules # with side effects

class Module(MixedModule):
    """CLR module"""

    appleveldefs = {
        'dotnetimporter': 'app_importer.importer'
        }
    
    interpleveldefs = {
        '_CliObject_internal': 'interp_clr.W_CliObject',
        'call_staticmethod': 'interp_clr.call_staticmethod',
        'load_cli_class': 'interp_clr.load_cli_class',
        'get_assemblies_info': 'interp_clr.get_assemblies_info',
        'AddReferenceByPartialName': 'interp_clr.AddReferenceByPartialName',
    }

    def startup(self, space):
        self.space.appexec([self], """(clr_module):
            import sys
            clr_module.get_assemblies_info() # load info for std assemblies
            sys.meta_path.append(clr_module.dotnetimporter())
            """)
