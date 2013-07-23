from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
            'ParseError' : 'app_error.ParseError',
            'ConversionError' : 'app_error.ConversionError',
            'GoalError' : 'app_error.GoalError',
            'UnknownPrologError' : 'app_error.UnknownPrologError',
    }

    interpleveldefs = {
        'CoreEngine'    : 'engine.W_CoreEngine',
        'Term'          : 'objects.W_Term',
        'Var'           : 'objects.W_Var',
    }
