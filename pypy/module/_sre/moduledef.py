from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'CODESIZE':       'space.newint(interp_sre.CODESIZE)',
        'MAGIC':          'space.newint(20031017)',
        'MAXREPEAT':      'space.newint(interp_sre.MAXREPEAT)',
        'OPCODES':        'space.newlist([space.newtext(s) if s is not None else space.w_None for s in interp_sre.ORDERED_OPCODE_NAMES])',
        'compile':        'interp_sre.W_SRE_Pattern',
        'getlower':       'interp_sre.w_getlower',
        'getcodesize':    'interp_sre.w_getcodesize',
    }
