#import py               # FINISHME - more thinking needed
raise ImportError
#skip("The _ssl module is only usable when running on the exact "
#     "same platform from which the ssl.py was computed.")

# This module is imported by socket.py. It should *not* be used
# directly.
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'ssl': 'interp_ssl.ssl',
    }

    appleveldefs = {
        '__doc__': 'app_ssl.__doc__',
        'sslerror': 'app_ssl.sslerror',
    }
    
    def buildloaders(cls):
        # init the SSL module
        from pypy.module._ssl.interp_ssl import _init_ssl, constants, HAVE_OPENSSL_RAND
        _init_ssl()
        
        for constant, value in constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
            
        if HAVE_OPENSSL_RAND:
            Module.interpleveldefs['RAND_add'] = "interp_ssl.RAND_add"
            Module.interpleveldefs['RAND_status'] = "interp_ssl.RAND_status"
            Module.interpleveldefs['RAND_egd'] = "interp_ssl.RAND_egd"
        
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
