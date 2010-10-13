from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'sslwrap': 'interp_ssl.sslwrap',
    }

    appleveldefs = {
        '__doc__': 'app_ssl.__doc__',
        'SSLError': 'app_ssl.SSLError',
    }

    @classmethod
    def buildloaders(cls):
        # init the SSL module
        from pypy.module._ssl.interp_ssl import constants, HAVE_OPENSSL_RAND

        for constant, value in constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % (value,)

        if HAVE_OPENSSL_RAND:
            Module.interpleveldefs['RAND_add'] = "interp_ssl.RAND_add"
            Module.interpleveldefs['RAND_status'] = "interp_ssl.RAND_status"
            Module.interpleveldefs['RAND_egd'] = "interp_ssl.RAND_egd"

        super(Module, cls).buildloaders()

    def startup(self, space):
        from pypy.rlib.ropenssl import init_ssl
        init_ssl()
