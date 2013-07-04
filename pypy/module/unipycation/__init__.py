from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
            'ParseError' : 'app_error.ParseError',
            'ConversionError' : 'app_error.ConversionError',
            'GoalError' : 'app_error.GoalError',
    }

    interpleveldefs = {
        'Engine'        : 'engine.W_Engine',
        'Term' : 'objects.W_Term',
    }
