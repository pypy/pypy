from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._hashlib.interp_hashlib import (
    algorithms, fetch_names, HAS_FAST_PKCS5_PBKDF2_HMAC)


class Module(MixedModule):
    interpleveldefs = {
        'new' : 'interp_hashlib.new',
        }

    appleveldefs = {
        }

    for name in algorithms:
        interpleveldefs['openssl_' + name] = 'interp_hashlib.new_' + name

    if HAS_FAST_PKCS5_PBKDF2_HMAC:
        interpleveldefs['pbkdf2_hmac'] = 'interp_hashlib.pbkdf2_hmac'

    def startup(self, space):
        w_meth_names = fetch_names(space)
        space.setattr(self, space.newtext('openssl_md_meth_names'), w_meth_names)
