from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'ssl': 'interp_ssl.ssl',
    }

    appleveldefs = {
        '__doc__': 'app_ssl.__doc__',
        'sslerror': 'app_ssl.sslerror',
    }

    @classmethod
    def buildloaders(cls):
        # init the SSL module
        from pypy.module._ssl.interp_ssl import constants, HAVE_OPENSSL_RAND

        for constant, value in constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value

        if HAVE_OPENSSL_RAND:
            Module.interpleveldefs['RAND_add'] = "interp_ssl.RAND_add"
            Module.interpleveldefs['RAND_status'] = "interp_ssl.RAND_status"
            Module.interpleveldefs['RAND_egd'] = "interp_ssl.RAND_egd"

        super(Module, cls).buildloaders()

    def startup(self, space):
        from pypy.module._ssl.interp_ssl import _init_ssl
        _init_ssl()
