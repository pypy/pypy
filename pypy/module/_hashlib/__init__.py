from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._hashlib.interp_hashlib import algorithms


class Module(MixedModule):
    interpleveldefs = {
        'new' : 'interp_hashlib.new',
        'HASH': 'interp_hashlib.W_Hash',
        }

    appleveldefs = {
        }

    for name in algorithms:
        interpleveldefs[name] = 'interp_hashlib.new_%s' % (name,)
