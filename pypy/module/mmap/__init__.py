from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'PAGESIZE': 'interp_mmap.PAGESIZE',
        'mmap': 'interp_mmap.mmap'
    }

    appleveldefs = {
        'ACCESS_READ': 'app_mmap.ACCESS_READ',
        'ACCESS_WRITE': 'app_mmap.ACCESS_WRITE',
        'ACCESS_COPY': 'app_mmap.ACCESS_COPY',
        'error': 'app_mmap.error'
    }
    
    def buildloaders(cls):
        import py            # REVIEWME
        py.test.skip("The mmap module is not ready: many methods do far too "
                     "much copying, and it uses 'pythonapi', which makes it "
                     "not translatable.")

        from pypy.module.mmap import interp_mmap
        import os

        Module.interpleveldefs["PAGESIZE"] = 'space.wrap(%r)' %\
            interp_mmap._get_page_size()
         
        if os.name == "posix":
            for constant, value in interp_mmap.constants.iteritems():
                Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

