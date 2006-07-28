# This module is imported by socket.py. It should *not* be used
# directly.
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'ssl': 'interp_ssl.ssl',
        'RAND_add': 'interp_ssl.RAND_add',
        'RAND_status': 'interp_ssl.RAND_status',
        'RAND_egd': 'interp_ssl.RAND_egd',
    }

    appleveldefs = {
        '__doc__': 'app_ssl.__doc__',
        'sslerror': 'app_ssl.sslerror',
    }
    
    def buildloaders(cls):
        # init the SSL module
        from pypy.module._ssl.interp_ssl import _init_ssl, constants
        _init_ssl()
        
        for constant, value in constants.iteritems():
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)
