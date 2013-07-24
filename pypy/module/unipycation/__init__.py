from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
            'ParseError' : 'app_error.ParseError',
            'ConversionError' : 'app_error.ConversionError',
            'PrologError' : 'app_error.PrologError',
    }

    interpleveldefs = {
        'CoreEngine'    : 'engine.W_CoreEngine',
        'Term'          : 'objects.W_Term',
        'Var'           : 'objects.W_Var',
    }
