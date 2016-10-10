import sys

from pypy.interpreter.mixedmodule import MixedModule
from pypy.module.imp.importing import get_pyc_magic
from rpython.rlib import rtime


class BuildersModule(MixedModule):
    appleveldefs = {}

    interpleveldefs = {
        "StringBuilder": "interp_builders.W_StringBuilder",
        "UnicodeBuilder": "interp_builders.W_UnicodeBuilder",
    }

class TimeModule(MixedModule):
    appleveldefs = {}
    interpleveldefs = {}
    if rtime.HAS_CLOCK_GETTIME:
        interpleveldefs["clock_gettime"] = "interp_time.clock_gettime"
        interpleveldefs["clock_getres"] = "interp_time.clock_getres"
        for name in rtime.ALL_DEFINED_CLOCKS:
            interpleveldefs[name] = "space.wrap(%d)" % getattr(rtime, name)


class ThreadModule(MixedModule):
    appleveldefs = {
        'signals_enabled': 'app_signal.signals_enabled',
    }
    interpleveldefs = {
        '_signals_enter':  'interp_signal.signals_enter',
        '_signals_exit':   'interp_signal.signals_exit',
    }


class IntOpModule(MixedModule):
    appleveldefs = {}
    interpleveldefs = {
        'int_add':         'interp_intop.int_add',
        'int_sub':         'interp_intop.int_sub',
        'int_mul':         'interp_intop.int_mul',
        'int_floordiv':    'interp_intop.int_floordiv',
        'int_mod':         'interp_intop.int_mod',
        'int_lshift':      'interp_intop.int_lshift',
        'int_rshift':      'interp_intop.int_rshift',
        'uint_rshift':     'interp_intop.uint_rshift',
    }


class OsModule(MixedModule):
    appleveldefs = {}
    interpleveldefs = {
        'real_getenv': 'interp_os.real_getenv'
    }


class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'attach_gdb'                : 'interp_magic.attach_gdb',
        'internal_repr'             : 'interp_magic.internal_repr',
        'bytebuffer'                : 'bytebuffer.bytebuffer',
        'identity_dict'             : 'interp_identitydict.W_IdentityDict',
        'debug_start'               : 'interp_debug.debug_start',
        'debug_print'               : 'interp_debug.debug_print',
        'debug_stop'                : 'interp_debug.debug_stop',
        'debug_print_once'          : 'interp_debug.debug_print_once',
        'debug_flush'               : 'interp_debug.debug_flush',
        'builtinify'                : 'interp_magic.builtinify',
        'hidden_applevel'           : 'interp_magic.hidden_applevel',
        'get_hidden_tb'             : 'interp_magic.get_hidden_tb',
        'lookup_special'            : 'interp_magic.lookup_special',
        'do_what_I_mean'            : 'interp_magic.do_what_I_mean',
        'validate_fd'               : 'interp_magic.validate_fd',
        'resizelist_hint'           : 'interp_magic.resizelist_hint',
        'newlist_hint'              : 'interp_magic.newlist_hint',
        'add_memory_pressure'       : 'interp_magic.add_memory_pressure',
        'newdict'                   : 'interp_dict.newdict',
        'reversed_dict'             : 'interp_dict.reversed_dict',
        'strategy'                  : 'interp_magic.strategy',  # dict,set,list
        'specialized_zip_2_lists'   : 'interp_magic.specialized_zip_2_lists',
        'set_debug'                 : 'interp_magic.set_debug',
        'locals_to_fast'            : 'interp_magic.locals_to_fast',
        'set_code_callback'         : 'interp_magic.set_code_callback',
        'save_module_content_for_future_reload':
                          'interp_magic.save_module_content_for_future_reload',
        'decode_long'               : 'interp_magic.decode_long',
        '_promote'                   : 'interp_magic._promote',
    }
    if sys.platform == 'win32':
        interpleveldefs['get_console_cp'] = 'interp_magic.get_console_cp'

    submodules = {
        "builders": BuildersModule,
        "time": TimeModule,
        "thread": ThreadModule,
        "intop": IntOpModule,
        "os": OsModule,
    }

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        if self.space.config.objspace.std.withmethodcachecounter:
            self.extra_interpdef('method_cache_counter',
                                 'interp_magic.method_cache_counter')
            self.extra_interpdef('reset_method_cache_counter',
                                 'interp_magic.reset_method_cache_counter')
            self.extra_interpdef('mapdict_cache_counter',
                                 'interp_magic.mapdict_cache_counter')
        PYC_MAGIC = get_pyc_magic(self.space)
        self.extra_interpdef('PYC_MAGIC', 'space.wrap(%d)' % PYC_MAGIC)
        try:
            from rpython.jit.backend import detect_cpu
            model = detect_cpu.autodetect()
            self.extra_interpdef('cpumodel', 'space.wrap(%r)' % model)
        except Exception:
            if self.space.config.translation.jit:
                raise
            else:
                pass   # ok fine to ignore in this case
        
        if self.space.config.translation.jit:
            features = detect_cpu.getcpufeatures(model)
            self.extra_interpdef('jit_backend_features',
                                    'space.wrap(%r)' % features)
