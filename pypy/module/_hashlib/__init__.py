from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._hashlib.interp_hashlib import algorithms


class Module(MixedModule):
    interpleveldefs = {
        'new' : 'interp_hashlib.new',
        }

    appleveldefs = {
        }

    for name in algorithms:
        interpleveldefs['openssl_' + name] = 'interp_hashlib.new_' + name

    def startup(self, space):
        from pypy.rlib.ropenssl import init_digests
        init_digests()
