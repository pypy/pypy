
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'StringIO':    'interp_stringio.StringIO',
        'InputType':   'interp_stringio.W_InputType',
        'OutputType':  'interp_stringio.W_OutputType',
    }
