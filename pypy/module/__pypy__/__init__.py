
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
from pypy.module.imp.importing import get_pyc_magic

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'internal_repr'             : 'interp_magic.internal_repr',
        'bytebuffer'                : 'bytebuffer.bytebuffer',
    }

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        if not self.space.config.translating:
            self.extra_interpdef('isfake', 'interp_magic.isfake')
            self.extra_interpdef('interp_pdb', 'interp_magic.interp_pdb')
        if self.space.config.objspace.std.withmethodcachecounter:
            self.extra_interpdef('method_cache_counter',
                                 'interp_magic.method_cache_counter')
            self.extra_interpdef('reset_method_cache_counter',
                                 'interp_magic.reset_method_cache_counter')
        PYC_MAGIC = get_pyc_magic(self.space)
        self.extra_interpdef('PYC_MAGIC', 'space.wrap(%d)' % PYC_MAGIC)
