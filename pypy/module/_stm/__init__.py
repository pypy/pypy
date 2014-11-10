
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'local': 'local.STMLocal',
        'count': 'count.count',
    }
