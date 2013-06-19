from pypy.interpreter.mixedmodule import MixedModule                            

class Module(MixedModule):

    appleveldefs = {
            'ParseError' : 'app_error.ParseError',
            'ConversionError' : 'app_error.ConversionError',
    }

    interpleveldefs = {
        'Engine'        : 'engine.W_Engine',        
    }
