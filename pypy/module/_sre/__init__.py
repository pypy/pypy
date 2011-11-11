from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    cannot_override_in_import_statements = True

    appleveldefs = {
    }

    interpleveldefs = {
        'CODESIZE':       'space.wrap(interp_sre.CODESIZE)',
        'MAGIC':          'space.wrap(interp_sre.MAGIC)',
        'compile':        'interp_sre.W_SRE_Pattern',
        'getlower':       'interp_sre.w_getlower',
        'getcodesize':    'interp_sre.w_getcodesize',
    }
