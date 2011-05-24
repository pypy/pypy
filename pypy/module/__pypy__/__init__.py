
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
from pypy.module.imp.importing import get_pyc_magic

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'internal_repr'             : 'interp_magic.internal_repr',
        'bytebuffer'                : 'bytebuffer.bytebuffer',
        'identity_dict'             : 'interp_identitydict.W_IdentityDict',
        'debug_start'               : 'interp_debug.debug_start',
        'debug_print'               : 'interp_debug.debug_print',
        'debug_stop'                : 'interp_debug.debug_stop',
        'debug_print_once'          : 'interp_debug.debug_print_once',
        'builtinify'                : 'interp_magic.builtinify',
        'lookup_special'            : 'interp_magic.lookup_special',
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
            if self.space.config.objspace.std.withmapdict:
                self.extra_interpdef('mapdict_cache_counter',
                                     'interp_magic.mapdict_cache_counter')
        PYC_MAGIC = get_pyc_magic(self.space)
        self.extra_interpdef('PYC_MAGIC', 'space.wrap(%d)' % PYC_MAGIC)
        #
        from pypy.jit.backend import detect_cpu
        model = detect_cpu.autodetect_main_model_and_size()
        self.extra_interpdef('cpumodel', 'space.wrap(%r)' % model)
