from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
        'template': 'app_sre.template',
    }

    interpleveldefs = {
        'CODESIZE':       'space.newint(interp_sre.CODESIZE)',
        'MAGIC':          'space.newint(20221023)',
        'MAXREPEAT':      'space.newint(interp_sre.MAXREPEAT)',
        'MAXGROUPS':      'space.newint(interp_sre.MAXGROUPS)',
        'OPCODES':        'space.newlist([space.newtext(s) if s is not None else space.w_None for s in interp_sre.ORDERED_OPCODE_NAMES])',
        'compile':        'interp_sre._sre_compile',
        'getcodesize':    'interp_sre.w_getcodesize',
        'ascii_iscased':  'interp_sre.w_ascii_iscased',
        'unicode_iscased':'interp_sre.w_unicode_iscased',
        'ascii_tolower':  'interp_sre.w_ascii_tolower',
        'unicode_tolower':'interp_sre.w_unicode_tolower',
    }
