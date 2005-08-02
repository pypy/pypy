from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    
    appleveldefs = {
        '__name__':       'app_sre.__name__',
        '__doc__':        'app_sre.__doc__',
        'CODESIZE':       'app_sre.CODESIZE',
        'MAGIC':          'app_sre.CODESIZE',
        'copyright':      'app_sre.copyright',
        'compile':        'app_sre.compile',
        'getcodesize':    'app_sre.getcodesize',
        'getlower':       'app_sre.getlower',
    }

    interpleveldefs = {
    }
