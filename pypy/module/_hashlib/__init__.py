from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._hashlib.interp_hashlib import algorithms


class Module(MixedModule):
    interpleveldefs = {
        'new' : 'interp_hashlib.new',
        'openssl_md_meth_names': 'interp_hashlib.get(space).w_meth_names'
        }

    appleveldefs = {
        }

    for name in algorithms:
        interpleveldefs['openssl_' + name] = 'interp_hashlib.new_' + name

    def startup(self, space):
        from rpython.rlib.ropenssl import init_digests
        init_digests()
