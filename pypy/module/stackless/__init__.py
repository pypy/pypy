
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'cstack_unwind':       'cstack.unwind',
        'cstack_frames_depth': 'cstack.frames_depth',
        'cstack_too_big':      'cstack.too_big',
        'cstack_check':        'cstack.check',
    }
