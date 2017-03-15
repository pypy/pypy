from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'CODESIZE':       'space.newint(interp_sre.CODESIZE)',
        'MAGIC':          'space.newint(20140917)',
        'MAXREPEAT':      'space.newint(interp_sre.MAXREPEAT)',
        'MAXGROUPS':      'space.newint(interp_sre.MAXGROUPS)',
        'compile':        'interp_sre.W_SRE_Pattern',
        'getlower':       'interp_sre.w_getlower',
        'getcodesize':    'interp_sre.w_getcodesize',
    }
