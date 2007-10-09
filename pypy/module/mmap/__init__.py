from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib import rmmap

class Module(MixedModule):
    interpleveldefs = {
        'PAGESIZE': 'space.wrap(interp_mmap.PAGESIZE)',
        'mmap': 'interp_mmap.mmap'
    }

    appleveldefs = {
        'ACCESS_READ': 'app_mmap.ACCESS_READ',
        'ACCESS_WRITE': 'app_mmap.ACCESS_WRITE',
        'ACCESS_COPY': 'app_mmap.ACCESS_COPY',
        'error': 'app_mmap.error'
    }
    
    def buildloaders(cls):
        from pypy.module.mmap import interp_mmap
        for constant, value in rmmap.constants.iteritems():
            if isinstance(value, int):
                Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

