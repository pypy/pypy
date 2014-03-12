from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'CODESIZE':       'space.wrap(interp_sre.CODESIZE)',
        'MAGIC':          'space.wrap(interp_sre.MAGIC)',
        'MAXREPEAT':      'space.wrap(interp_sre.MAXREPEAT)',
        'compile':        'interp_sre.W_SRE_Pattern',
        'getlower':       'interp_sre.w_getlower',
        'getcodesize':    'interp_sre.w_getcodesize',
    }
