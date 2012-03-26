import sys

from pypy.interpreter.mixedmodule import MixedModule
from pypy.module.imp.importing import get_pyc_magic


class BuildersModule(MixedModule):
    appleveldefs = {}

    interpleveldefs = {
        "StringBuilder": "interp_builders.W_StringBuilder",
        "UnicodeBuilder": "interp_builders.W_UnicodeBuilder",
    }

class TimeModule(MixedModule):
    appleveldefs = {}
    interpleveldefs = {}
    if sys.platform.startswith("linux"):
        from pypy.module.__pypy__ import interp_time
        interpleveldefs["clock_gettime"] = "interp_time.clock_gettime"
        interpleveldefs["clock_getres"] = "interp_time.clock_getres"
        for name in [
            "CLOCK_REALTIME", "CLOCK_MONOTONIC", "CLOCK_MONOTONIC_RAW",
            "CLOCK_PROCESS_CPUTIME_ID", "CLOCK_THREAD_CPUTIME_ID"
        ]:
            if getattr(interp_time, name) is not None:
                interpleveldefs[name] = "space.wrap(interp_time.%s)" % name


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
        'do_what_I_mean'            : 'interp_magic.do_what_I_mean',
        'list_strategy'             : 'interp_magic.list_strategy',
    }

    submodules = {
        "builders": BuildersModule,
        "time": TimeModule,
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
