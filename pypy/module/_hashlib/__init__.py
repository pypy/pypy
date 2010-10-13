from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._hashlib import interp_hashlib


class Module(MixedModule):
    interpleveldefs = {
        'new' : 'interp_hashlib.new',
        'HASH': 'interp_hashlib.W_Hash',
        }

    appleveldefs = {
        }

    for name in interp_hashlib.algorithms:
        interpleveldefs[name] = getattr(interp_hashlib, 'new_' + name)
